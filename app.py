
from __future__ import annotations

import base64
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from bindu.data.auth_repository import AuthRepository
from bindu.data.local_cache import LocalCache
from bindu.data.lesson_repository import LessonRepository
from bindu.data.progress_repository import ProgressRepository
from bindu.data.supabase_client import load_env_from_streamlit_secrets
from bindu.domain import gamification
from bindu.domain.models import ExerciseType

APP_DIR = Path(__file__).parent
LOGO_ICON = APP_DIR / "assets" / "bindu_favicon.png"
LOGO_FULL = APP_DIR / "assets" / "bindu_logo_full.png"

st.set_page_config(
    page_title="BINDU - learn Nepali",
    page_icon=str(LOGO_ICON) if LOGO_ICON.exists() else "🏔️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Nepali flag colors (crimson + blue) — used throughout for a consistent
# "bindu" (journey) look instead of generic app colors.
NEPAL_CRIMSON = "#DC143C"
NEPAL_BLUE = "#003893"
UNIT_COLORS = ["#0038A8", "#DA251D", "#046A38", "#B8860B", "#7A288A"]

# A learner gets this many "lives" per lesson *attempt* (independent of the
# slower-refilling account-wide hearts shown in the sidebar). Miss this many
# questions in one lesson and the attempt ends right there as failed — the
# rest of the questions aren't shown, nothing is saved, and the lesson stays
# locked/incomplete until retried. This only works out to a fair rule when
# every lesson actually has hearts+2 questions, so content/units.final.yaml
# is padded to exactly 7 exercises per lesson.
LESSON_HEARTS = gamification.MAX_HEARTS

# Lesson "lives" are shown as plates of dal bhat instead of hearts — a full
# plate for a life you still have, an empty plate for one you've used up.
DAL_BHAT_FULL = "🍛"
DAL_BHAT_EMPTY = "🍽️"

# A handful of Nepali sayings shown around the app for a bit of local
# flavor — rotates based on the lesson/unit index so it isn't static.
NEPALI_PROVERBS = [
    ("बाटो हिँडेरै बन्छ।", "The path is made by walking it."),
    ("सिकाइको कुनै अन्त्य हुँदैन।", "Learning never ends."),
    ("एक थोपा पानीले भाँडो भर्छ।", "A pot fills one drop at a time — small steps add up."),
    ("जहाँ चाहना छ, त्यहाँ बाटो छ।", "Where there's a will, there's a way."),
]

NODE_STYLE = """
<style>
.node-wrap { display: flex; justify-content: center; margin: 4px 0 0 0; }
.node-circle {
    width: 64px; height: 64px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px; margin: 0 auto;
    box-shadow: 0 4px 0 rgba(0,0,0,0.15);
    border: 3px solid rgba(0,0,0,0.08);
}
.node-done { background: #E8A33D; }
.node-current { background: #ffd23f; animation: pulse 1.6s infinite; }
.node-locked { background: #d9d9d9; box-shadow: none; }
@keyframes pulse {
    0% { box-shadow: 0 4px 0 rgba(0,0,0,0.15), 0 0 0 0 rgba(255,210,63,0.6); }
    70% { box-shadow: 0 4px 0 rgba(0,0,0,0.15), 0 0 0 14px rgba(255,210,63,0); }
    100% { box-shadow: 0 4px 0 rgba(0,0,0,0.15), 0 0 0 0 rgba(255,210,63,0); }
}
.node-label { text-align: center; font-size: 12px; margin-top: 2px; color: #666; }
.you-are-here {
    text-align: center; font-size: 11px; font-weight: 700;
    color: #ffab00; letter-spacing: 0.5px; margin-top: -2px;
}
.unit-banner {
    padding: 14px 18px; border-radius: 14px; color: white; margin: 18px 0 14px 0;
    display: flex; justify-content: space-between; align-items: center;
}
.unit-banner .title { font-weight: 700; font-size: 17px; }
.unit-banner .sub { font-size: 12px; opacity: 0.85; }
</style>
"""

# ---------------------------------------------------------------------------
# App chrome — makes the page read as a native app screen instead of a
# website built on Streamlit. Injected once, on every screen (including the
# auth gate), before anything else renders.
#
# What this buys us:
#   - The browser-y bits (hamburger menu, "Deploy" button, footer credit,
#     the thin colored "loading" bar) are hidden — `client.toolbarMode =
#     "minimal"` in config.toml does most of this already; the CSS here is
#     a belt-and-braces fallback for older Streamlit versions/embeds.
#   - Content is capped to a phone-width column and centered, with a
#     subtle card/shadow around it on wide screens, like a phone mockup.
#   - Buttons, inputs and metrics get rounder corners, bolder weight and
#     a bit of shadow/lift instead of Streamlit's flat default widgets.
# ---------------------------------------------------------------------------
APP_CHROME_CSS = """
<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    visibility: hidden; height: 0;
}
[data-testid="stHeader"] { background: transparent; }

html, body, [class*="css"] { font-family: 'Nunito', 'Source Sans Pro', sans-serif; }

/* Phone-width column, centered, with a soft "device" shadow on wide screens */
.block-container {
    max-width: 480px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    margin: 0 auto;
}
@media (min-width: 900px) {
    .block-container {
        box-shadow: 0 0 40px rgba(0,0,0,0.08);
        border-radius: 24px;
        background: #ffffff;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        margin-top: 16px;
        margin-bottom: 16px;
    }
}

/* App-style buttons: pill-shaped, bold, a little lift */
.stButton > button {
    border-radius: 14px;
    font-weight: 700;
    padding: 0.6rem 1rem;
    box-shadow: 0 3px 0 rgba(0,0,0,0.12);
    transition: transform 0.05s ease-in-out;
    border: none;
}
.stButton > button:active { transform: translateY(2px); box-shadow: none; }

/* Exercise answer options (multiple-choice) — selecting one used to turn
   it the same glossy crimson as the app's primary CTA buttons, which read
   as more "look at me" than a simple selected-state should. A flat, calm
   blue instead: clearly marks the pick without competing for attention. */
div[class*="st-key-mcopt_"] .stButton > button[kind="primary"] {
    background: #2C5F8A !important;
    color: #ffffff !important;
    box-shadow: none !important;
    border: none !important;
}

/* Segmented-control look for the "Go to" nav radio inside the settings popover */
.stPopover .stRadio > div {
    flex-direction: row;
    gap: 6px;
    background: #F0F2F6;
    padding: 4px;
    border-radius: 12px;
}
.stPopover .stRadio label {
    flex: 1;
    text-align: center;
    border-radius: 9px;
    padding: 6px 0;
    margin: 0;
}
.stPopover .stRadio label[data-checked="true"] { background: #ffffff; }

/* Tabs (login/signup) as app-style pill toggle instead of underlined web tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #F0F2F6; padding: 4px; border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px; padding: 8px 0; font-weight: 700;
}
.stTabs [aria-selected="true"] { background: #ffffff; }

/* Metrics as rounded cards instead of plain website-style stat blocks */
[data-testid="stMetric"] {
    background: #F6F7FB;
    border-radius: 14px;
    padding: 10px 12px;
}
</style>
"""

# Extra CSS layered on top of APP_CHROME_CSS when the user picks "Dark" in
# Settings. Streamlit's own widgets (buttons, inputs, alerts, popovers,
# tabs...) are compiled against its *config-level* light theme, so they
# don't automatically follow a CSS variable we set after the fact — that's
# why an earlier version of this only recolored a few surfaces and left
# things like button backgrounds dark with their original dark text
# (dark-on-dark = invisible). This version explicitly repaints every
# surface AND its text together, in the same rule, so nothing is left
# dark-on-dark or light-on-light.
DARK_BG = "#0e1117"
DARK_SURFACE = "#1c1f26"
DARK_SURFACE_2 = "#262730"
DARK_BORDER = "#3a3d4a"
DARK_TEXT = "#fafafa"

DARK_THEME_CSS = f"""
<style>
:root {{
    --background-color: {DARK_BG};
    --secondary-background-color: {DARK_SURFACE_2};
    --text-color: {DARK_TEXT};
    --primary-color: {NEPAL_CRIMSON};
}}

/* Base app surface */
.stApp, [data-testid="stAppViewContainer"], body {{
    background-color: {DARK_BG} !important;
}}
/* stHeader is a fixed overlay bar pinned to the top of the viewport, not
   part of normal document flow — painting it opaque (as the bulk rule
   above used to, before this fix) makes it a solid bar that sits on top
   of and visually chops off whatever content scrolls underneath it (e.g.
   the top of the identity row/avatar). It must stay transparent so
   there's nothing to chop with, same as APP_CHROME_CSS already intends. */
[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container {{ background: {DARK_BG} !important; }}
@media (min-width: 900px) {{
    .block-container {{
        background: {DARK_SURFACE} !important;
        box-shadow: 0 0 40px rgba(0,0,0,0.55) !important;
    }}
}}

/* Force every bit of ordinary text to a readable light color */
.stApp p, .stApp span, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
    color: {DARK_TEXT} !important;
}}

/* Buttons — surface AND text repainted together. Broad `.stApp button`
   catch-all included as a fallback for any button Streamlit renders with
   a wrapper/testid this list doesn't already name (icon-only buttons,
   popover triggers, etc.) — without it, odd-one-out buttons can end up
   stuck on a white background with no visible label. */
.stApp button, .stButton > button, [data-testid^="baseButton-"] {{
    background-color: {DARK_SURFACE_2} !important;
    color: {DARK_TEXT} !important;
    border: 1px solid {DARK_BORDER} !important;
}}
.stApp button[kind="primary"], .stButton > button[kind="primary"], [data-testid="baseButton-primary"] {{
    background: {NEPAL_CRIMSON} !important;
    color: #ffffff !important;
    border: none !important;
}}
.stApp button:disabled {{ opacity: 0.45; }}

/* Text inputs / text areas */
input, textarea,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{
    background-color: {DARK_SURFACE} !important;
    color: {DARK_TEXT} !important;
    border-color: {DARK_BORDER} !important;
}}
input::placeholder, textarea::placeholder {{ color: #8a8f9c !important; }}

/* Alerts: success / error / warning / info boxes */
[data-testid="stAlert"] {{ background: {DARK_SURFACE} !important; }}
[data-testid="stAlert"] * {{ color: {DARK_TEXT} !important; }}

/* Popover / expander / tab panels */
[data-testid="stPopoverBody"], [data-testid="stExpander"] {{
    background: {DARK_SURFACE} !important;
    color: {DARK_TEXT} !important;
    border-color: {DARK_BORDER} !important;
}}
[data-testid="stMetric"], .stTabs [data-baseweb="tab-list"], .stPopover .stRadio > div {{
    background: {DARK_SURFACE_2} !important;
}}
.stTabs [aria-selected="true"], .stPopover .stRadio label[data-checked="true"] {{
    background: {DARK_BORDER} !important;
}}

/* Progress bar track */
[data-testid="stProgress"] > div > div {{ background-color: {DARK_SURFACE_2} !important; }}

/* Path-map lesson labels, which are hardcoded for light mode in NODE_STYLE */
.node-label {{ color: #cfd3dc !important; }}
</style>
"""

# Mirror of DARK_THEME_CSS, applied when the user picks "Light" in Settings.
# Needed because .streamlit/config.toml now compiles Streamlit's *native*
# widgets (buttons, inputs, popovers, tabs, metrics...) against a dark base
# theme by default — so "Light" can no longer just mean "don't add the dark
# overrides". Without this, picking Light left native widgets rendered with
# their dark-theme colors while our custom markdown cards flipped back to
# light (theme_colors()), producing the exact light/dark mismatch this is
# meant to avoid. This explicitly repaints every surface back to light,
# the same surface-and-text-together way DARK_THEME_CSS does for dark.
LIGHT_BG = "#FFFFFF"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_SURFACE_2 = "#F6F7FB"
LIGHT_BORDER = "#E0E2E9"
LIGHT_TEXT = "#262730"

LIGHT_THEME_CSS = f"""
<style>
:root {{
    --background-color: {LIGHT_BG};
    --secondary-background-color: {LIGHT_SURFACE_2};
    --text-color: {LIGHT_TEXT};
    --primary-color: {NEPAL_CRIMSON};
}}

.stApp, [data-testid="stAppViewContainer"], body {{
    background-color: {LIGHT_BG} !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container {{ background: {LIGHT_BG} !important; }}
@media (min-width: 900px) {{
    .block-container {{
        background: {LIGHT_SURFACE} !important;
        box-shadow: 0 0 40px rgba(0,0,0,0.08) !important;
    }}
}}

.stApp p, .stApp span, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
    color: {LIGHT_TEXT} !important;
}}

.stApp button, .stButton > button, [data-testid^="baseButton-"] {{
    background-color: {LIGHT_SURFACE_2} !important;
    color: {LIGHT_TEXT} !important;
    border: 1px solid {LIGHT_BORDER} !important;
}}
.stApp button[kind="primary"], .stButton > button[kind="primary"], [data-testid="baseButton-primary"] {{
    background: {NEPAL_CRIMSON} !important;
    color: #ffffff !important;
    border: none !important;
}}
.stApp button:disabled {{ opacity: 0.45; }}

input, textarea,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{
    background-color: {LIGHT_SURFACE} !important;
    color: {LIGHT_TEXT} !important;
    border-color: {LIGHT_BORDER} !important;
}}
input::placeholder, textarea::placeholder {{ color: #888888 !important; }}

[data-testid="stAlert"] {{ background: {LIGHT_SURFACE_2} !important; }}
[data-testid="stAlert"] * {{ color: {LIGHT_TEXT} !important; }}

[data-testid="stPopoverBody"], [data-testid="stExpander"] {{
    background: {LIGHT_SURFACE} !important;
    color: {LIGHT_TEXT} !important;
    border-color: {LIGHT_BORDER} !important;
}}
[data-testid="stMetric"], .stTabs [data-baseweb="tab-list"], .stPopover .stRadio > div {{
    background: {LIGHT_SURFACE_2} !important;
}}
.stTabs [aria-selected="true"], .stPopover .stRadio label[data-checked="true"] {{
    background: #ffffff !important;
}}

[data-testid="stProgress"] > div > div {{ background-color: {LIGHT_SURFACE_2} !important; }}

.node-label {{ color: #666666 !important; }}
</style>
"""


def get_theme() -> str:
    """The user's chosen theme ("light" or "dark"), set from the Settings
    popover in render_top_bar and persisted for the session. Defaults to
    light — BINDU ships light-mode-first."""
    return st.session_state.get("theme", "light")


def theme_colors() -> dict:
    """A few hand-picked colors this app's custom (non-Streamlit-native)
    cards use, so they don't end up light-mode-only when dark is picked."""
    if get_theme() == "dark":
        return {"card_bg": DARK_SURFACE_2, "muted_text": "#a9adba", "body_text": DARK_TEXT}
    return {"card_bg": "#F6F7FB", "muted_text": "#888888", "body_text": "#262730"}


def inject_app_chrome() -> None:
    # Streamlit's native widgets are compiled against the light base theme
    # in .streamlit/config.toml, but both branches still get an explicit
    # repaint here so switching to "Dark" in Settings doesn't leave any
    # widget on its light-mode colors.
    css = APP_CHROME_CSS + (DARK_THEME_CSS if get_theme() == "dark" else LIGHT_THEME_CSS)
    st.markdown(css, unsafe_allow_html=True)


def render_streak_result(streak_extended: bool, streak: int) -> None:
    """Shows the streak outcome after a lesson, the way a real app makes the
    streak feel like something you *maintained* today — not just a number
    that ticks up. Only fires the "new day" celebration once per calendar
    day (streak_extended is only True the first time today, since
    record_activity_and_update_streak leaves the streak untouched on any
    later completion the same day); every other completion still earns XP,
    it just quietly confirms the streak is already safe for today.
    """
    if streak_extended:
        st.markdown(
            f"""<div style="text-align:center;padding:14px 10px;margin:10px 0;
                        border-radius:16px;background:linear-gradient(135deg,#ff9a3c,#ff5f6d);
                        color:white;box-shadow:0 4px 14px rgba(255,95,109,0.35);">
                    <div style="font-size:2.2rem;line-height:1;animation:flame-pop 0.5s ease-out;">🔥</div>
                    <div style="font-weight:800;font-size:1.1rem;margin-top:2px;">
                        Streak day {streak} secured!
                    </div>
                    <div style="font-size:0.85rem;opacity:0.9;">Come back tomorrow to keep it alive.</div>
                </div>
                <style>
                @keyframes flame-pop {{
                    0% {{ transform: scale(0.4); opacity: 0; }}
                    60% {{ transform: scale(1.15); opacity: 1; }}
                    100% {{ transform: scale(1); }}
                }}
                </style>""",
            unsafe_allow_html=True,
        )
    else:
        colors = theme_colors()
        st.markdown(
            f"""<div style="text-align:center;padding:8px 10px;margin:10px 0;
                        border-radius:14px;background:{colors['card_bg']};color:{colors['muted_text']};">
                    🔥 Streak already secured today — day {streak}
                </div>""",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Text-to-speech: every answer option carries its own "hidden" voice. We
# don't need pre-recorded audio for this — the options are already real
# Nepali script (see content/units.final.yaml), so the browser's built-in
# Web Speech API can pronounce them on demand, for free, the instant an
# option is tapped.
# ---------------------------------------------------------------------------

def speak_nepali(text: str, nonce: int = 0) -> None:
    """Speaks `text` aloud in the user's browser using the Web Speech API.

    Rendered as an invisible components.html snippet. `nonce` should change
    every time the same text needs to be re-spoken (e.g. tapping the same
    option twice) — Streamlit skips re-running a component's <script> when
    the HTML it renders is byte-for-byte identical to last time, so we bake
    the nonce into the markup purely to force a fresh execution.
    """
    if not text:
        return
    # Escape for safe embedding inside a JS template literal.
    safe_text = (
        text.replace("\\", "\\\\").replace("`", "\\`").replace("</", "<\\/")
    )
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const synth = window.speechSynthesis;
                if (!synth) return;
                synth.cancel();
                const utter = new SpeechSynthesisUtterance(`{safe_text}`);
                utter.lang = 'ne-NP';
                utter.rate = 0.85;
                synth.speak(utter);
            }} catch (e) {{ /* Web Speech API unsupported in this browser */ }}
        }})();
        </script>
        <!-- nonce:{nonce} -->
        """,
        height=0,
    )


def _escape_html_text(text: str) -> str:
    """Minimal escaping for placing plain text inside HTML markup (not an
    attribute, not a JS string — see speak_nepali's escaping for that)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_question(prompt: str, audio_url: str | None, key: str) -> None:
    """Renders the question text with a speaker icon that plays `audio_url`.

    The audio autoplays once when a *new* question appears, and the same
    speaker icon lets the learner replay it on demand with one click.

    The trick: this component's entire HTML output is a pure function of
    (prompt, audio_url, key) — nothing else about the surrounding page
    state leaks in. Streamlit's components.html skips remounting the
    iframe when its HTML is byte-for-byte identical to the last render
    (same mechanism speak_nepali above relies on), so tapping an option or
    a token elsewhere on the page — which reruns this whole function with
    identical arguments — does NOT recreate the <audio> element or refire
    autoplay. Only advancing to a genuinely new question (different key,
    different prompt/audio) produces different HTML, which remounts the
    iframe and autoplays exactly once for that question. The button stays
    clickable across those in-between reruns because the iframe itself
    was never torn down.
    """
    # Rendered inside its own iframe (components.html), which does NOT
    # inherit Streamlit's page theme — so `color:inherit` used to resolve to
    # plain black text on a transparent box. That's invisible against
    # Streamlit's dark theme (black-on-black). Kept deliberately plain —
    # solid black card, white text — instead of a themed gradient, so it
    # reads the same in both light and dark mode without guessing colors.
    safe_prompt = _escape_html_text(prompt)
    card_style = (
        f"display:flex;align-items:flex-start;gap:10px;"
        f"font-family:'Source Sans Pro',sans-serif;font-size:1.15rem;font-weight:600;"
        f"color:#ffffff;background:#000000;"
        f"padding:12px 16px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.25);"
    )
    if not audio_url:
        components.html(
            f"""<div style="{card_style}"><span>🏔️</span><span>{safe_prompt}</span></div>""",
            height=54,
        )
        return
    safe_url = audio_url.replace('"', "&quot;")
    components.html(
        f"""
        <div style="{card_style}">
            <span>🏔️</span>
            <span>{safe_prompt}</span>
            <button id="replay-{key}" title="Replay audio" style="
                    background:none;border:none;cursor:pointer;font-size:1.25rem;
                    line-height:1;padding:0;margin-left:auto;flex-shrink:0;color:#ffffff;">🔊</button>
        </div>
        <audio id="audio-{key}" src="{safe_url}" autoplay></audio>
        <script>
        (function() {{
            const audio = document.getElementById('audio-{key}');
            const btn = document.getElementById('replay-{key}');
            btn.addEventListener('click', function() {{
                audio.currentTime = 0;
                audio.play().catch(function(e) {{ /* needs a user gesture in some browsers — this click IS one */ }});
            }});
        }})();
        </script>
        """,
        height=64,
    )


# ---------------------------------------------------------------------------
# Wiring: cached resources + a stand-in for auth (a text-entered user id).
# ---------------------------------------------------------------------------

@st.cache_resource
def get_cache() -> LocalCache:
    return LocalCache()


@st.cache_resource
def get_lesson_repo() -> LessonRepository:
    return LessonRepository(get_cache())


@st.cache_resource
def get_progress_repo() -> ProgressRepository:
    return ProgressRepository(get_cache())


@st.cache_resource
def get_auth_repo() -> AuthRepository:
    return AuthRepository(get_cache())


def get_user_id() -> str:
    """The signed-in username, which doubles as the progress/stats key.

    Only valid once render_auth_gate() has confirmed a session — main()
    always calls that first, so by the time any lesson/profile code runs
    this is guaranteed to be set.
    """
    return st.session_state["auth_user"]


# How often the app pulls fresh curriculum from Supabase into the shared
# local cache. Curriculum content changes rarely (a content-authoring
# reseed, not a per-user action), so this doesn't need to be instant —
# it just needs to happen without anyone having to know a button exists.
CURRICULUM_SYNC_INTERVAL_SECONDS = 300  # 5 minutes


@st.cache_data(ttl=CURRICULUM_SYNC_INTERVAL_SECONDS)
def _synced_at() -> float:
    """Refreshes curriculum + retries any pending progress/stats writes.

    st.cache_data (unlike st.session_state) is shared across every user's
    session on this deployment, and its TTL expires independently of any
    one browser tab. So the *first* page load after the TTL lapses re-runs
    this for everyone, and every load in between reuses the cached result
    with no network call — periodic and automatic, with no button needed.
    """
    get_lesson_repo().refresh_from_remote()
    get_progress_repo().sync_pending_writes()
    return time.time()


def init_backend() -> None:
    load_env_from_streamlit_secrets()
    _synced_at()


@st.cache_data
def _logo_b64(path: Path) -> str:
    """Base64-encodes a logo image so it can be inlined in raw HTML markdown
    (st.image can't sit inside a centered flex div the way an <img> tag can)."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _logo_img_tag(path: Path, height_px: int) -> str:
    """An <img> tag for a BINDU logo asset. The mark itself is solid black
    (it's a wordmark/pin, not a themed icon), so on the dark theme's near-
    black background it would otherwise vanish — this wraps it in a small
    white backing plate whenever dark mode is active so it's always visible,
    and renders it bare (no plate) on the light theme where it already
    reads fine against the white page."""
    if not path.exists():
        return ""
    b64 = _logo_b64(path)
    img = (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="height:{height_px}px;vertical-align:middle;" alt="BINDU logo"/>'
    )
    if get_theme() == "dark":
        pad = max(4, height_px // 8)
        return (
            f'<div style="display:inline-flex;background:#ffffff;'
            f'border-radius:{pad * 2}px;padding:{pad}px {pad * 1.5}px;">{img}</div>'
        )
    return img


# ---------------------------------------------------------------------------
# Auth gate — a real (if simple) username/password login, so progress, XP,
# hearts and streaks are tied to an account instead of a free-typed name
# anyone could reuse. Blocks the rest of the app until signed in.
# ---------------------------------------------------------------------------

def render_auth_gate() -> None:
    logo_tag = _logo_img_tag(LOGO_FULL, 96) or '<div style="font-size:2.4rem;">🙏🏔️</div>'
    st.markdown(
        f"""<div style="text-align:center;padding:18px 0 6px 0;">
                {logo_tag}
                <div style="font-size:1.5rem;font-weight:700;">नमस्ते! Welcome to BINDU</div>
                <div style="opacity:0.75;font-size:0.95rem;">Sign in to save your streak, hearts and XP.</div>
            </div>""",
        unsafe_allow_html=True,
    )

    st.caption("Log in with your username and password")

    auth_repo = get_auth_repo()
    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            result = auth_repo.log_in(username, password)
            if result.ok:
                st.session_state.auth_user = result.username
                st.session_state.auth_display_name = result.display_name
                st.rerun()
            else:
                st.error(result.error)

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username", key="signup_username")
            new_display_name = st.text_input("Display name (optional)", key="signup_display_name")
            new_password = st.text_input("Choose a password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if new_password != confirm_password:
                st.error("Passwords don't match.")
            else:
                result = auth_repo.sign_up(new_username, new_password, new_display_name)
                if result.ok:
                    st.session_state.auth_user = result.username
                    st.session_state.auth_display_name = result.display_name
                    st.success(f"Account created — स्वागत छ, {result.display_name}! 🎉")
                    st.rerun()
                else:
                    st.error(result.error)


# ---------------------------------------------------------------------------
# Top bar: identity + live stats, pinned top-left in the main screen — the
# way a real app keeps who-you-are, your streak and XP always in view,
# instead of tucked into a collapsible sidebar the user has to go open
# (and which is hidden by default on mobile).
# ---------------------------------------------------------------------------

def render_top_bar() -> None:
    progress_repo = get_progress_repo()
    user_id = get_user_id()
    stats = progress_repo.refill_hearts_if_due(user_id)
    level = gamification.level_for_xp(stats.xp)
    display_name = st.session_state.get("auth_display_name", user_id)
    initial = (display_name or "?")[0].upper()

    col_id, col_streak, col_xp, col_flag, col_settings, col_logo = st.columns(
        [2.6, 1.3, 1.6, 0.8, 0.9, 2.8]
    )

    with col_id:
        colors = theme_colors()
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                                background:linear-gradient(135deg,{NEPAL_CRIMSON},{NEPAL_BLUE});
                                color:white;display:flex;align-items:center;justify-content:center;
                                font-weight:800;">{initial}</div>
                    <div style="line-height:1.15;">
                        <div style="font-weight:700;font-size:0.95rem;">{display_name}</div>
                        <div style="font-weight:400;font-size:0.72rem;color:{colors['muted_text']};">Level {level}</div>
                    </div>
                </div>""",
            unsafe_allow_html=True,
        )
    with col_streak:
        st.markdown(
            f"""<div style="text-align:center;">
                    <div style="font-size:1.25rem;line-height:1;">🔥</div>
                    <div style="font-weight:700;font-size:0.8rem;">{stats.streak}</div>
                </div>""",
            unsafe_allow_html=True,
        )
    with col_xp:
        st.markdown(
            f"""<div style="text-align:center;">
                    <div style="font-size:1.25rem;line-height:1;">⭐</div>
                    <div style="font-weight:700;font-size:0.8rem;">{stats.xp} XP</div>
                </div>""",
            unsafe_allow_html=True,
        )
    with col_flag:
        st.markdown(
            """<div style="text-align:center;font-size:1.5rem;line-height:1;padding-top:4px;" title="Nepal">🇳🇵</div>""",
            unsafe_allow_html=True,
        )
    with col_settings:
        with st.popover("⚙️"):
            st.markdown(f"**🙏 {display_name}**")
            st.caption(f"Level {level} · {stats.xp} XP · streak {stats.streak}🔥")
            st.divider()
            st.radio(
                "Go to", ["Path map", "Profile"], key="section",
                label_visibility="collapsed",
            )
            st.divider()
            st.caption("Theme")
            current_theme = get_theme()
            theme_choice = st.radio(
                "Theme", ["Light", "Dark"],
                index=0 if current_theme == "light" else 1,
                key="theme_choice", horizontal=True,
                label_visibility="collapsed",
            )
            chosen_theme = "dark" if theme_choice == "Dark" else "light"
            if chosen_theme != current_theme:
                st.session_state["theme"] = chosen_theme
                st.rerun()
            st.divider()
            if st.button("Log out", use_container_width=True, key="settings_logout"):
                for k in ("auth_user", "auth_display_name"):
                    st.session_state.pop(k, None)
                st.rerun()

    with col_logo:
        logo_tag = _logo_img_tag(LOGO_ICON, 34)
        if logo_tag:
            st.markdown(
                f"""<div style="text-align:right;">{logo_tag}</div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Path map page — a winding, level-by-level game path (Duolingo-style)
# ---------------------------------------------------------------------------

def render_path_map() -> None:
    st.markdown(NODE_STYLE, unsafe_allow_html=True)
    lesson_repo = get_lesson_repo()
    progress_repo = get_progress_repo()
    user_id = get_user_id()

    units = lesson_repo.get_units()
    if not units:
        st.info("No curriculum loaded yet. Seed Supabase (see `content/seed_supabase.py`) "
                 "— it'll appear here automatically within a few minutes.")
        return

    progress = progress_repo.get_progress_for_user(user_id)

    # Single sequential path: flatten every lesson across every unit (in
    # order) and unlock one at a time — a lesson is only playable once the
    # lesson immediately before it on the path has been completed.
    all_lessons = [lesson for unit in units for lesson in unit.lessons]
    unlocked_so_far = True
    current_lesson_id = None
    for lesson in all_lessons:
        state = progress.get(lesson.id, {"completed": False, "stars": 0})
        lesson.locked = not unlocked_so_far
        if unlocked_so_far and not state["completed"] and current_lesson_id is None:
            current_lesson_id = lesson.id
        unlocked_so_far = unlocked_so_far and state["completed"]

    completed_count = sum(1 for p in progress.values() if p["completed"])
    total_count = len(all_lessons)
    st.header("Your path")
    st.progress(
        completed_count / total_count if total_count else 0,
        text=f"{completed_count}/{total_count} lessons cleared",
    )
    nepali, english = NEPALI_PROVERBS[completed_count % len(NEPALI_PROVERBS)]
    st.caption(f"🇳🇵 *{nepali}* — “{english}”")

    for u_idx, unit in enumerate(units):
        color = unit.color_theme or UNIT_COLORS[u_idx % len(UNIT_COLORS)]
        unit_done = sum(1 for l in unit.lessons if progress.get(l.id, {}).get("completed"))
        st.markdown(
            f"""<div class="unit-banner" style="background:{color}">
                    <div><div class="title">UNIT {u_idx + 1} · {unit.name}</div>
                    <div class="sub">{unit_done}/{len(unit.lessons)} lessons complete</div></div>
                </div>""",
            unsafe_allow_html=True,
        )

        # Zig-zag the nodes left/center/right for that winding-path feel.
        offsets = [1, 0, 2, 0, 1]
        for l_idx, lesson in enumerate(unit.lessons):
            state = progress.get(lesson.id, {"completed": False, "stars": 0})
            is_current = lesson.id == current_lesson_id

            if state["completed"]:
                # A marigold rosette instead of a plain checkmark — sayapatri
                # (marigold) garlands and tika are how completed effort is
                # marked in Nepal, so "done" reads as a small blessing/award
                # rather than a generic UI tick.
                node_class, emoji = "node-done", "🏵️"
            elif is_current:
                node_class, emoji = "node-current", "🔊"
            else:
                node_class, emoji = "node-locked", "🔒"

            slot = offsets[l_idx % len(offsets)]
            cols = st.columns([1, 1, 1])
            with cols[slot]:
                st.markdown(
                    f"""<div class="node-wrap"><div class="node-circle {node_class}">{emoji}</div></div>
                        <div class="node-label">{'⭐' * state['stars'] if state['completed'] else lesson.name}</div>""",
                    unsafe_allow_html=True,
                )
                if is_current:
                    st.markdown('<div class="you-are-here">YOU ARE HERE</div>', unsafe_allow_html=True)
                button_label = "Start 🔊" if is_current else ("Review" if state["completed"] else "Locked 🔒")
                if st.button(
                    button_label, key=f"lesson-{lesson.id}", use_container_width=True,
                    disabled=lesson.locked,
                ):
                    st.session_state.active_lesson_id = lesson.id


# ---------------------------------------------------------------------------
# Lesson runner — its own full screen, not tacked onto the bottom of the
# path map. Clicking "Start" should feel like opening into a new view, the
# way a real lesson app snaps you into a focused, distraction-free mode.
# ---------------------------------------------------------------------------

def render_lesson_screen(lesson_id: int) -> None:
    lesson_repo = get_lesson_repo()
    progress_repo = get_progress_repo()
    progress = progress_repo.get_progress_for_user(get_user_id())

    all_lessons = [lesson for unit in lesson_repo.get_units() for lesson in unit.lessons]
    unlocked_so_far = True
    for lesson in all_lessons:
        state = progress.get(lesson.id, {"completed": False, "stars": 0})
        lesson.locked = not unlocked_so_far
        unlocked_so_far = unlocked_so_far and state["completed"]

    active_lesson = next((l for l in all_lessons if l.id == lesson_id), None)
    if active_lesson is not None and active_lesson.locked:
        st.warning("That lesson is locked — finish the previous one first.")
        st.session_state.active_lesson_id = None
        return

    top_left, top_right = st.columns([1, 6])
    with top_left:
        if st.button("❌", key="exit_lesson", help="Exit lesson"):
            for k in (f"exercise_index_{lesson_id}", f"correct_count_{lesson_id}", f"lesson_hearts_{lesson_id}"):
                st.session_state.pop(k, None)
            st.session_state.active_lesson_id = None
            st.rerun()
    with top_right:
        if active_lesson is not None:
            st.markdown(f"**{active_lesson.name}**")

    render_lesson(lesson_id)


def render_lesson(lesson_id: int) -> None:
    lesson_repo = get_lesson_repo()
    progress_repo = get_progress_repo()
    user_id = get_user_id()

    exercises = lesson_repo.get_exercises_for_lesson(lesson_id)
    if not exercises:
        st.warning("This lesson has no exercises yet.")
        return

    key = f"exercise_index_{lesson_id}"
    correct_key = f"correct_count_{lesson_id}"
    hearts_key = f"lesson_hearts_{lesson_id}"
    st.session_state.setdefault(key, 0)
    st.session_state.setdefault(correct_key, 0)
    st.session_state.setdefault(hearts_key, LESSON_HEARTS)

    def _reset_attempt() -> None:
        for k in (key, correct_key, hearts_key):
            st.session_state.pop(k, None)

    lesson_hearts = st.session_state[hearts_key]
    total = len(exercises)

    # Out of hearts for THIS lesson attempt: 5 wrong answers ends it right
    # there, whether or not every question has been shown yet — mirrors how
    # hearts work in the reference Duolingo UX. Nothing is saved and the
    # lesson stays locked/incomplete until retried.
    if lesson_hearts <= 0:
        st.markdown(f"<div style='font-size:2rem;text-align:center;'>{DAL_BHAT_EMPTY * LESSON_HEARTS}</div>",
                     unsafe_allow_html=True)
        st.error(
            f"Out of hearts — {st.session_state[correct_key]}/{total} correct before you ran out. "
            "यो पाठ पूरा भएन। This lesson isn't complete yet."
        )
        if st.button("Retry lesson", key=f"retry_{lesson_id}"):
            _reset_attempt()
            st.rerun()
        return

    idx = st.session_state[key]
    if idx >= len(exercises):
        correct_count = st.session_state[correct_key]
        # Reaching the last question with hearts still left (checked above)
        # means the attempt passed — progress is saved, XP is awarded, and
        # the next lesson unlocks. Stars reward accuracy without gating
        # completion on it.
        stars = round(3 * correct_count / total)

        stats_before = progress_repo.get_or_create_stats(user_id)
        level_before = gamification.level_for_xp(stats_before.xp)
        today_str = datetime.now(timezone.utc).date().isoformat()
        already_active_today = stats_before.last_active == today_str

        xp_earned = 10 * correct_count
        progress_repo.mark_lesson_complete(user_id, lesson_id, stars)
        stats_after = progress_repo.add_xp(user_id, amount=xp_earned)
        # XP is credited for every lesson regardless, but the streak itself
        # only advances once per calendar day — record_activity_and_update_streak
        # already enforces that (same-day calls leave it unchanged).
        streak_stats = progress_repo.record_activity_and_update_streak(user_id)
        level_after = gamification.level_for_xp(stats_after.xp)

        accuracy = round(100 * correct_count / total)
        st.balloons()

        # A small summary card instead of one plain success line — accuracy,
        # XP and stars laid out the way Duolingo's end-of-lesson recap does,
        # topped with the same marigold rosette used for a "done" node on
        # the path map and a Nepali line of congratulations, so finishing a
        # lesson reads as a small, specific accomplishment rather than a
        # generic "you passed" banner.
        colors = theme_colors()
        st.markdown(
            f"""<div style="background:{colors['card_bg']};border-radius:18px;
                        padding:22px 20px;text-align:center;margin:8px 0 16px 0;">
                    <div style="font-size:2.6rem;line-height:1;">🏵️</div>
                    <div style="font-weight:800;font-size:1.25rem;margin-top:6px;
                        color:{colors['body_text']};">
                        साबास! Lesson complete!
                    </div>
                    <div style="font-size:0.9rem;color:{colors['muted_text']};margin-top:2px;">
                        Well done — {correct_count}/{total} correct
                    </div>
                    <div style="display:flex;justify-content:center;gap:22px;margin-top:16px;">
                        <div>
                            <div style="font-weight:800;font-size:1.1rem;color:{colors['body_text']};">
                                {'⭐' * stars}{'☆' * (3 - stars)}
                            </div>
                            <div style="font-size:0.75rem;color:{colors['muted_text']};">STARS</div>
                        </div>
                        <div>
                            <div style="font-weight:800;font-size:1.1rem;color:{colors['body_text']};">
                                +{xp_earned} XP
                            </div>
                            <div style="font-size:0.75rem;color:{colors['muted_text']};">EARNED</div>
                        </div>
                        <div>
                            <div style="font-weight:800;font-size:1.1rem;color:{colors['body_text']};">
                                {accuracy}%
                            </div>
                            <div style="font-size:0.75rem;color:{colors['muted_text']};">ACCURACY</div>
                        </div>
                    </div>
                </div>""",
            unsafe_allow_html=True,
        )
        render_streak_result(streak_extended=not already_active_today, streak=streak_stats.streak)
        if level_after > level_before:
            st.success(f"🎉 LEVEL UP! You've reached Level {level_after}!")

        if st.button("Continue", key=f"continue_{lesson_id}"):
            _reset_attempt()
            st.session_state.active_lesson_id = None
            st.rerun()
        return

    st.markdown(
        f"<div style='text-align:right;font-size:1.3rem;'>{DAL_BHAT_FULL * lesson_hearts}{DAL_BHAT_EMPTY * (LESSON_HEARTS - lesson_hearts)}</div>",
        unsafe_allow_html=True,
    )

    exercise = exercises[idx]
    st.subheader(f"Lesson · Question {idx + 1} of {len(exercises)}")
    st.progress(idx / len(exercises))
    render_question(exercise.prompt, exercise.audio_url, key=f"{lesson_id}_{idx}")

    correct = False
    submitted = False

    if exercise.type == ExerciseType.MULTIPLE_CHOICE:
        st.caption("Tap an option to hear it pronounced and select it as your answer:")
        choice_key = f"mc_choice_{lesson_id}_{idx}"
        nonce_key = f"mc_speak_nonce_{lesson_id}_{idx}"
        st.session_state.setdefault(choice_key, None)
        st.session_state.setdefault(nonce_key, 0)

        for opt_idx, option in enumerate(exercise.options):
            is_selected = st.session_state[choice_key] == option
            label = f"✅  {option}" if is_selected else option
            if st.button(
                label, key=f"mcopt_{lesson_id}_{idx}_{opt_idx}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state[choice_key] = option
                st.session_state[nonce_key] += 1

        choice = st.session_state[choice_key]
        # Re-speak the currently selected option every time it (or the nonce)
        # changes — this is the "voice hidden inside the answer" behavior.
        if choice:
            speak_nepali(choice, nonce=st.session_state[nonce_key])

        if st.button("Check", key=f"check_{lesson_id}_{idx}", disabled=choice is None):
            from bindu.domain.exercise_validator import check_multiple_choice
            correct = check_multiple_choice(choice, exercise.answer)
            submitted = True
            # Selection state is per-exercise-instance; clear it so the next
            # question (or a retry) starts with nothing pre-selected.
            st.session_state.pop(choice_key, None)
            st.session_state.pop(nonce_key, None)

    elif exercise.type == ExerciseType.WORD_BANK:
        st.caption("Tap the tokens below in the correct order (each tap also speaks it):")
        order_key = f"wb_order_{lesson_id}_{idx}"
        tok_nonce_key = f"wb_speak_nonce_{lesson_id}_{idx}"
        tok_last_key = f"wb_speak_last_{lesson_id}_{idx}"
        st.session_state.setdefault(order_key, [])
        st.session_state.setdefault(tok_nonce_key, 0)
        # order_key stores the *indices* chosen so far (into exercise.tokens),
        # not the token text — some word-bank exercises repeat a word (e.g.
        # the same Nepali particle twice in one sentence), and tracking by
        # text broke two things at once: every occurrence of a repeated word
        # shared one st.button key (StreamlitDuplicateElementKey crash), and
        # tapping one occurrence removed *all* copies from the remaining
        # bank (value-based membership, not position-based).
        chosen_indices = st.session_state[order_key]

        # Fixed-height answer preview: reserved space stays the same
        # whether 0 words or all of them are chosen, so this line never
        # pushes the tiles/buttons below it up or down as you build the
        # sentence.
        chosen_text = " ".join(exercise.tokens[i] for i in chosen_indices)
        # The placeholder markup is built as a plain variable, not inline
        # inside the f-string below — an f-string's {expression} part can't
        # contain a backslash-escaped quote on Python versions before 3.12
        # (PEP 701), and this app needs to run on older Python too.
        placeholder_html = '<span style="opacity:0.5;">tap tokens below…</span>'
        st.markdown(
            f"<div style='min-height:2.4em;font-size:1.05rem;'>"
            f"{chosen_text or placeholder_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Always lay out ALL tiles in their original positions (not just the
        # remaining ones) and just disable the ones already used. Removing
        # tiles from the grid shrank st.columns(...) as you picked words,
        # which changed this row's height and made Check/Reset drift up or
        # down below it — keeping every slot present keeps the row (and
        # everything under it) a fixed height throughout the question.
        token_cols = st.columns(len(exercise.tokens))
        for tok_idx, col in enumerate(token_cols):
            with col:
                used = tok_idx in chosen_indices
                if st.button(
                    exercise.tokens[tok_idx],
                    key=f"tok_{lesson_id}_{idx}_{tok_idx}",
                    disabled=used,
                    use_container_width=True,
                ):
                    st.session_state[order_key].append(tok_idx)
                    st.session_state[tok_last_key] = exercise.tokens[tok_idx]
                    st.session_state[tok_nonce_key] += 1
                    st.rerun()

        # Speak whichever token was tapped most recently.
        if st.session_state.get(tok_last_key):
            speak_nepali(st.session_state[tok_last_key], nonce=st.session_state[tok_nonce_key])

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Reset order", key=f"reset_{lesson_id}_{idx}"):
                st.session_state[order_key] = []
                st.session_state.pop(tok_last_key, None)
                st.rerun()
        with col_b:
            if st.button("Check", key=f"check_{lesson_id}_{idx}",
                         disabled=len(st.session_state[order_key]) != len(exercise.tokens)):
                from bindu.domain.exercise_validator import check_word_bank
                ordered_tokens = [exercise.tokens[i] for i in st.session_state[order_key]]
                correct = check_word_bank(ordered_tokens, exercise.answer)
                submitted = True
                st.session_state.pop(tok_last_key, None)
                st.session_state.pop(tok_nonce_key, None)

    if submitted:
        if correct:
            st.success("Correct! 🎉 राम्रो!")
            st.session_state[correct_key] += 1
        else:
            st.error(f"Not quite — correct answer: {' '.join(exercise.answer)}")
            st.session_state[hearts_key] -= 1
            # Also deducts from the slower-refilling, account-wide heart pool
            # shown in the sidebar (separate from this lesson's 5 lives).
            progress_repo.deduct_heart(user_id)
        st.session_state[key] += 1
        st.rerun()


# ---------------------------------------------------------------------------
# Profile page
# ---------------------------------------------------------------------------

def render_profile() -> None:
    st.header("🙏 Profile")
    progress_repo = get_progress_repo()
    user_id = get_user_id()
    stats = progress_repo.get_or_create_stats(user_id)
    progress = progress_repo.get_progress_for_user(user_id)
    level = gamification.level_for_xp(stats.xp)

    col1, col2, col3 = st.columns(3)
    col1.metric("Level", level)
    col2.metric("XP", stats.xp)
    col3.metric("Streak", f"{stats.streak} 🔥")

    completed = sum(1 for p in progress.values() if p["completed"])
    st.write(f"**Lessons completed:** {completed}")
    st.write(f"**Last active:** {stats.last_active or 'never'}")


# ---------------------------------------------------------------------------

def main() -> None:
    inject_app_chrome()
    init_backend()

    if "auth_user" not in st.session_state:
        render_auth_gate()
        return

    section = st.session_state.get("section", "Path map")
    active_lesson_id = st.session_state.get("active_lesson_id")

    # While a lesson is open, the top bar (streak/XP/settings) is hidden
    # rather than skipped entirely. The nav radio and theme radio inside it
    # are keyed widgets — if the whole function is skipped some runs (in
    # a lesson) and called on others (on the path map), Streamlit tears
    # down and recreates their session state every time a lesson opens or
    # closes, which is a good way to hit odd mid-session errors. Keeping
    # it mounted every run and just hiding it with CSS avoids that churn
    # while still giving the lesson the whole screen visually.
    if active_lesson_id:
        st.markdown(
            '<style>div[class*="st-key-top_bar_wrap"] { display: none; }</style>',
            unsafe_allow_html=True,
        )
    with st.container(key="top_bar_wrap"):
        render_top_bar()

    if section == "Profile":
        render_profile()
    elif active_lesson_id:
        render_lesson_screen(active_lesson_id)
    else:
        render_path_map()


def render_fatal_error() -> None:
    """Shown instead of Streamlit's own error UI when something unexpected
    breaks mid-render. Deliberately never includes the exception type,
    message, or traceback — those are for the server log only (see the
    except block below) — so whatever actually went wrong internally,
    the person using the app only ever sees one calm, actionable message.
    """
    inject_app_chrome()  # in case the crash happened before main() got to this
    st.error(
        "Something went wrong loading this page. Please try again — if it "
        "keeps happening, use the button below to reset and start fresh."
    )
    if st.button("Reload BINDU", key="fatal_error_reload"):
        # Keep the person signed in and their theme choice; clear everything
        # else (in-progress lesson state, stray widget keys, etc.) since
        # that's the state most likely to have caused an unexpected crash.
        keep = {"auth_user", "auth_display_name", "theme"}
        for k in list(st.session_state.keys()):
            if k not in keep:
                st.session_state.pop(k, None)
        st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Full traceback goes to the server-side log for debugging — never
        # to the person's browser.
        logging.getLogger("bindu").exception("Unhandled error in BINDU")
        render_fatal_error()