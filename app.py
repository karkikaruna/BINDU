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
SPEAKER_ICON = APP_DIR / "assets" / "speakerrrr.png"

st.set_page_config(
    page_title="BINDU",
    page_icon=str(LOGO_ICON)  ,
    layout="centered",
    initial_sidebar_state="collapsed",
)

BINDU_PRIMARY = "#C2703D"  
BINDU_PRIMARY_DARK = "#AD5F30"

NEPAL_CRIMSON = BINDU_PRIMARY
NEPAL_BLUE = "#E0A458"
UNIT_COLORS = ["#C2703D", "#2F6F73", "#A14E68", "#B08968", "#3D6B8C"]


LESSON_HEARTS = gamification.MAX_HEARTS

MIN_CORRECT_TO_PASS = 4

DAL_BHAT_FULL = "🍛"
DAL_BHAT_EMPTY = "🍽️"

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
.node-current { background: #ffd23f; box-shadow: 0 4px 0 rgba(0,0,0,0.15), 0 0 0 4px rgba(255,210,63,0.35); }
.node-locked { background: #d9d9d9; box-shadow: none; }
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


APP_CHROME_CSS = """
<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    visibility: hidden; height: 0;
}
[data-testid="stHeader"] { background: transparent; }

html, body, [class*="css"] { font-family: 'Nunito', 'Source Sans Pro', sans-serif; }


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


div[data-testid="stButton"] button,
div[data-testid="stFormSubmitButton"] button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    box-shadow: 0 2px 0 rgba(0,0,0,0.08) !important;
    transition: transform 0.05s ease-in-out !important;
    border: none !important;
}
div[data-testid="stButton"] button:active,
div[data-testid="stFormSubmitButton"] button:active {
    transform: translateY(1px) !important; box-shadow: none !important;
}

.st-key-settings_open div[data-testid="stButton"] button {
    border-radius: 50% !important;
    width: 40px !important; height: 40px !important;
    padding: 0 !important;
    background: #F3F1EC !important;
    border: 1px solid #E7E3DA !important;
    box-shadow: 0 2px 0 rgba(0,0,0,0.06) !important;
}
.st-key-settings_open div[data-testid="stButton"] button:hover { background: #EAE6DC !important; }
.st-key-settings_open div[data-testid="stButton"] button:active {
    transform: translateY(1px) !important; box-shadow: none !important;
}


div[data-testid="stFormSubmitButton"] button,
button[kind="primary"] {
    background: #C2703D !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 3px 0 rgba(150, 84, 40, 0.45) !important;
}
div[data-testid="stFormSubmitButton"] button:hover,
button[kind="primary"]:hover {
    background: #AD5F30 !important;
}
div[data-testid="stFormSubmitButton"] button:active,
button[kind="primary"]:active {
    box-shadow: 0 1px 0 rgba(150, 84, 40, 0.45) !important;
}


div[class*="st-key-mcopt_"] button[kind="primary"] {
    background: #4B5B6B !important;
    color: #ffffff !important;
    box-shadow: none !important;
    border: none !important;
}

[data-testid="stDialog"] .stRadio > div {
    flex-direction: row;
    gap: 6px;
    background: #F3F1EC;
    padding: 4px;
    border-radius: 12px;
}
[data-testid="stDialog"] .stRadio label {
    flex: 1;
    text-align: center;
    border-radius: 9px;
    padding: 6px 0;
    margin: 0;
}
[data-testid="stDialog"] .stRadio label[data-checked="true"] { background: #ffffff; }

[data-testid="stTabs"] [role="tablist"] {
    gap: 4px !important;
    background: #F3F1EC !important;
    padding: 4px !important;
    border-radius: 12px !important;
    border: none !important;
}
[data-testid="stTab"] {
    border-radius: 9px !important;
    padding: 8px 0 !important;
    font-weight: 600 !important;
    justify-content: center !important;
    box-shadow: none !important;
    flex: 1 !important;
}
[data-testid="stTab"][aria-selected="true"] {
    background: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}

[data-testid="stTab"] .react-aria-SelectionIndicator {
    display: none !important;
}


[data-testid="stForm"] {
    border-radius: 18px !important;
    padding: 22px 20px 18px 20px !important;
    border: 1px solid #ECEDF2 !important;
    box-shadow: 0 6px 20px rgba(20, 20, 30, 0.05) !important;
}


[data-testid="stForm"] [data-testid="stWidgetLabel"] p {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #6b7280 !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 2px !important;
}

[data-testid="stForm"] [data-testid="stTextInputRootElement"] {
    border-radius: 11px !important;
    border: 1.5px solid #D8B9A0 !important;
    box-shadow: none !important;
    transition: border-color 0.12s ease-in-out, box-shadow 0.12s ease-in-out !important;
}
[data-testid="stForm"] [data-testid="stTextInputRootElement"]:focus-within {
    border-color: #C2703D !important;
    box-shadow: 0 0 0 3px rgba(194, 112, 61, 0.15) !important;
}
[data-testid="stForm"] [data-testid="stTextInputField"] {
    padding: 0.6rem 0.85rem !important;
}

[data-testid="stMetric"] {
    background: #F6F7FB;
    border-radius: 14px;
    padding: 10px 12px;
}
</style>
"""

#for dark
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

.stApp, [data-testid="stAppViewContainer"], body {{
    background-color: {DARK_BG} !important;
}}

[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container {{ background: {DARK_BG} !important; }}
@media (min-width: 900px) {{
    .block-container {{
        background: {DARK_SURFACE} !important;
        box-shadow: 0 0 40px rgba(0,0,0,0.55) !important;
    }}
}}


.stApp p, .stApp span, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
    color: {DARK_TEXT} !important;
}}


.stApp button, .stButton > button, [data-testid^="baseButton-"] {{
    background-color: {DARK_SURFACE_2} !important;
    color: {DARK_TEXT} !important;
    border: 1px solid {DARK_BORDER} !important;
}}
.stApp button[kind="primary"], .stButton > button[kind="primary"], [data-testid="baseButton-primary"] {{
    background: #C2703D !important;
    color: #ffffff !important;
    border: none !important;
}}
.stApp button:disabled {{ opacity: 0.45; }}


input, textarea,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{
    background-color: {DARK_SURFACE} !important;
    color: {DARK_TEXT} !important;
    border-color: {DARK_BORDER} !important;
}}
input::placeholder, textarea::placeholder {{ color: #8a8f9c !important; }}


[data-testid="stAlert"] {{ background: {DARK_SURFACE} !important; }}
[data-testid="stAlert"] * {{ color: {DARK_TEXT} !important; }}


[data-testid="stDialog"], [data-testid="stExpander"] {{
    background: {DARK_SURFACE} !important;
    color: {DARK_TEXT} !important;
    border-color: {DARK_BORDER} !important;
}}
[data-testid="stMetric"], [data-testid="stTabs"] [role="tablist"], [data-testid="stDialog"] .stRadio > div {{
    background: {DARK_SURFACE_2} !important;
}}
[data-testid="stTab"][aria-selected="true"], [data-testid="stDialog"] .stRadio label[data-checked="true"] {{
    background: {DARK_BORDER} !important;
}}

[data-testid="stProgress"] > div > div {{ background-color: {DARK_SURFACE_2} !important; }}


.node-label {{ color: #cfd3dc !important; }}
</style>
"""

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
    background: #C2703D !important;
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

[data-testid="stDialog"], [data-testid="stExpander"] {{
    background: {LIGHT_SURFACE} !important;
    color: {LIGHT_TEXT} !important;
    border-color: {LIGHT_BORDER} !important;
}}
[data-testid="stMetric"], [data-testid="stTabs"] [role="tablist"], [data-testid="stDialog"] .stRadio > div {{
    background: {LIGHT_SURFACE_2} !important;
}}
[data-testid="stTab"][aria-selected="true"], [data-testid="stDialog"] .stRadio label[data-checked="true"] {{
    background: #ffffff !important;
}}

[data-testid="stProgress"] > div > div {{ background-color: {LIGHT_SURFACE_2} !important; }}

.node-label {{ color: #666666 !important; }}
</style>
"""


def get_theme() -> str:

    return st.session_state.get("theme", "light")


def theme_colors() -> dict:

    if get_theme() == "dark":
        return {"card_bg": DARK_SURFACE_2, "muted_text": "#a9adba", "body_text": DARK_TEXT}
    return {"card_bg": "#F6F7FB", "muted_text": "#888888", "body_text": "#262730"}


def inject_app_chrome() -> None:

    css = APP_CHROME_CSS + (DARK_THEME_CSS if get_theme() == "dark" else LIGHT_THEME_CSS)
    st.markdown(css, unsafe_allow_html=True)


def render_streak_result(streak_extended: bool, streak: int) -> None:

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
                    🔥 Streak already secured today-day {streak}
                </div>""",
            unsafe_allow_html=True,
        )



def speak_nepali(text: str, nonce: int = 0) -> None:

    if not text:
        return
  
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
 
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_question(prompt: str, audio_url: str | None, key: str, autoplay: bool = True) -> None:
   
    safe_prompt = _escape_html_text(prompt)
    card_style = (
        f"display:flex;align-items:flex-start;gap:10px;"
        f"font-family:'Source Sans Pro',sans-serif;font-size:1.15rem;font-weight:600;"
        f"color:#ffffff;background:#000000;"
        f"padding:12px 16px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.25);"
    )
    if not audio_url:
        components.html(
            f"""<div style="{card_style}"><span>{safe_prompt}</span></div>""",
            height=54,
        )
        return
    safe_url = audio_url.replace('"', "&quot;")
    speaker_icon = _speaker_img_tag(22)
    autoplay_attr = "autoplay" if autoplay else ""
    components.html(
        f"""
        <div style="{card_style}">
            <span>{safe_prompt}</span>
            <button id="replay-{key}" title="Replay audio" style="
                    background:none;border:none;cursor:pointer;
                    line-height:1;padding:0;margin-left:auto;flex-shrink:0;
                    display:flex;align-items:center;">{speaker_icon}</button>
        </div>
        <audio id="audio-{key}" src="{safe_url}" {autoplay_attr}></audio>
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



CURRICULUM_SYNC_INTERVAL_SECONDS = 300  # 5 minutes


@st.cache_data(ttl=CURRICULUM_SYNC_INTERVAL_SECONDS)
def _synced_at() -> float:

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


def _speaker_img_tag(size_px: int) -> str:
   
    if not SPEAKER_ICON.exists():
        return "🔊"
    b64 = _logo_b64(SPEAKER_ICON)
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:{size_px}px;height:{size_px}px;vertical-align:middle;" '
        f'alt="Speaker"/>'
    )



def render_auth_gate() -> None:

    logo_tag = _logo_img_tag(LOGO_FULL, 96) or '<div style="font-size:2.4rem;">🙏🏔️</div>'
    st.markdown(
        f"""<div style="text-align:center;padding:18px 0 6px 0;">
                {logo_tag}
                <div style="font-size:1.5rem;font-weight:700;">नमस्कार! Welcome to BINDU</div>
                <div style="opacity:0.75;font-size:0.95rem;">Sign in or login with your credentials.</div>
            </div>""",
        unsafe_allow_html=True,
    )

    auth_repo = get_auth_repo()
    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
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
            submitted = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted:
            if new_password != confirm_password:
                st.error("Passwords don't match.")
            else:
                result = auth_repo.sign_up(new_username, new_password, new_display_name)
                if result.ok:

                    st.session_state.auth_user = result.username
                    st.session_state.auth_display_name = result.display_name
                    st.rerun()
                else:
                    st.error(result.error)



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
                                background:linear-gradient(135deg,#C2703D,#E0A458);
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
        @st.dialog("Settings")
        def _settings_dialog() -> None:
            st.markdown(f"**{display_name}**")
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

        if st.button("⚙️", key="settings_open"):
            _settings_dialog()

    with col_logo:
        logo_tag = _logo_img_tag(LOGO_ICON, 34)
        if logo_tag:
            st.markdown(
                f"""<div style="text-align:right;">{logo_tag}</div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)


def render_path_map() -> None:
    st.markdown(NODE_STYLE, unsafe_allow_html=True)
    lesson_repo = get_lesson_repo()
    progress_repo = get_progress_repo()
    user_id = get_user_id()

    units = lesson_repo.get_units()
    if not units:

        logging.getLogger("bindu").warning(
            "render_path_map: local curriculum cache is empty for user_id=%s", user_id
        )
        st.info("Lessons are on their way — please check back in a few minutes.")
        return

    progress = progress_repo.get_progress_for_user(user_id)


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
    
    st.progress(
        completed_count / total_count if total_count else 0,
        text=f"{completed_count}/{total_count} lessons cleared",
    )
    
    for u_idx, unit in enumerate(units):
        color = UNIT_COLORS[u_idx % len(UNIT_COLORS)]
        unit_done = sum(1 for l in unit.lessons if progress.get(l.id, {}).get("completed"))
        st.markdown(
            f"""<div class="unit-banner" style="background:{color}">
                    <div><div class="title">UNIT {u_idx + 1} · {unit.name}</div>
                    <div class="sub">{unit_done}/{len(unit.lessons)} lessons complete</div></div>
                </div>""",
            unsafe_allow_html=True,
        )

       
        offsets = [1, 0, 2, 0, 1]
        for l_idx, lesson in enumerate(unit.lessons):
            state = progress.get(lesson.id, {"completed": False, "stars": 0})
            is_current = lesson.id == current_lesson_id

            if state["completed"]:

                node_class, emoji = "node-done", "🌼"
            elif is_current:
                node_class, emoji = "node-current", "▶️"
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
                button_label = "Start" if is_current else ("Review" if state["completed"] else "Locked 🔒")
                if st.button(
                    button_label, key=f"lesson-{lesson.id}", use_container_width=True,
                    disabled=lesson.locked,
                ):
                    st.session_state.active_lesson_id = lesson.id
                    st.rerun()



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
            for k in (
                f"queue_{lesson_id}", f"queue_pos_{lesson_id}", f"correct_set_{lesson_id}",
                f"attempts_{lesson_id}", f"lesson_hearts_{lesson_id}", f"first_try_{lesson_id}",
            ):
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

    total = len(exercises)


    queue_key = f"queue_{lesson_id}"
    pos_key = f"queue_pos_{lesson_id}"
    correct_set_key = f"correct_set_{lesson_id}"
    attempts_key = f"attempts_{lesson_id}"
    hearts_key = f"lesson_hearts_{lesson_id}"
    first_try_key = f"first_try_{lesson_id}"
    st.session_state.setdefault(queue_key, list(range(total)))
    st.session_state.setdefault(pos_key, 0)
    st.session_state.setdefault(correct_set_key, set())
    st.session_state.setdefault(attempts_key, {})
    st.session_state.setdefault(hearts_key, LESSON_HEARTS)
    st.session_state.setdefault(first_try_key, set())

    def _reset_attempt() -> None:
        for k in (queue_key, pos_key, correct_set_key, attempts_key, hearts_key, first_try_key):
            st.session_state.pop(k, None)


    lesson_hearts = st.session_state[hearts_key]
    queue = st.session_state[queue_key]
    pos = st.session_state[pos_key]
    feedback_key = f"feedback_{lesson_id}_{pos}" if pos < len(queue) else None
    pending_feedback = st.session_state.get(feedback_key) if feedback_key else None

    out_of_hearts = lesson_hearts <= 0
    queue_finished = pos >= len(queue)
    correct_so_far = len(st.session_state[correct_set_key])

    passed_on_hearts_out = out_of_hearts and correct_so_far >= MIN_CORRECT_TO_PASS

    if pending_feedback is None and out_of_hearts and not passed_on_hearts_out:
        st.markdown(f"<div style='font-size:2rem;text-align:center;'>{DAL_BHAT_EMPTY * LESSON_HEARTS}</div>",
                     unsafe_allow_html=True)
        st.error(
            f"Out of hearts, {correct_so_far}/{total} correct before you ran out. "
            
        )
        if st.button("Retry lesson", key=f"retry_{lesson_id}"):
            _reset_attempt()
            st.rerun()
        return

    if pending_feedback is None and (queue_finished or passed_on_hearts_out):

        first_try_count = len(st.session_state[first_try_key])

        stars = round(3 * first_try_count / total)

        stats_before = progress_repo.get_or_create_stats(user_id)
        level_before = gamification.level_for_xp(stats_before.xp)
        today_str = datetime.now(timezone.utc).date().isoformat()
        already_active_today = stats_before.last_active == today_str


        xp_earned = 10 * first_try_count + 5 * (total - first_try_count)
        progress_repo.mark_lesson_complete(user_id, lesson_id, stars)
        stats_after = progress_repo.add_xp(user_id, amount=xp_earned)

        streak_stats = progress_repo.record_activity_and_update_streak(user_id)
        level_after = gamification.level_for_xp(stats_after.xp)

        accuracy = round(100 * first_try_count / total)
        if passed_on_hearts_out:
            st.info(
                f"You ran out of hearts, {correct_so_far}/{total} correct "
                
            )
        st.balloons()


        colors = theme_colors()
        st.markdown(
            f"""<div style="background:{colors['card_bg']};border-radius:18px;
                        padding:22px 20px;text-align:center;margin:8px 0 16px 0;">
                    <div style="font-size:2.6rem;line-height:1;">🏵️</div>
                    <div style="font-weight:800;font-size:1.25rem;margin-top:6px;
                        color:{colors['body_text']};">
                        well done! 
                    </div>
                    <div style="font-size:0.9rem;color:{colors['muted_text']};margin-top:2px;">
                        {first_try_count}/{total} correct on the first try
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
            st.success(f"LEVEL UP! You've reached Level {level_after}!")

        if st.button("Continue", key=f"continue_{lesson_id}"):
            _reset_attempt()
            st.session_state.active_lesson_id = None
            st.rerun()
        return

    st.markdown(
        f"<div style='text-align:right;font-size:1.3rem;'>{DAL_BHAT_FULL * lesson_hearts}{DAL_BHAT_EMPTY * (LESSON_HEARTS - lesson_hearts)}</div>",
        unsafe_allow_html=True,
    )

    exercise_idx = queue[pos]
    exercise = exercises[exercise_idx]

    locked = pending_feedback is not None
    st.subheader(f"Lesson · Question {pos + 1} of {len(queue)}")
    if not locked and st.session_state[attempts_key].get(exercise_idx, 0) > 0:
        st.caption("🔁 Let's try that one again")
    st.progress(len(st.session_state[correct_set_key]) / total)
    render_question(
        exercise.prompt, exercise.audio_url,
        key=f"{lesson_id}_{exercise_idx}_{pos}",
        autoplay=not locked,
    )

    correct = False
    submitted = False
    result: dict | None = None

    if exercise.type == ExerciseType.MULTIPLE_CHOICE:
        st.caption("Tap an option to hear it pronounced and select it as your answer:")
        choice_key = f"mc_choice_{lesson_id}_{pos}"
        nonce_key = f"mc_speak_nonce_{lesson_id}_{pos}"
        st.session_state.setdefault(choice_key, None)
        st.session_state.setdefault(nonce_key, 0)

        selected_option = pending_feedback["selected"] if locked else st.session_state[choice_key]

        for opt_idx, option in enumerate(exercise.options):
            is_selected = selected_option == option
            label = option
            if locked and is_selected:
                label = f"{'.' if pending_feedback['correct'] else '❌'} {option}"
            elif locked and not pending_feedback["correct"] and option == pending_feedback["answer_text"]:
                label = f" {option}"
            if locked:
                st.button(
                    label, key=f"mcopt_{lesson_id}_{pos}_{opt_idx}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    disabled=True,
                )
            elif st.button(
                label, key=f"mcopt_{lesson_id}_{pos}_{opt_idx}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state[choice_key] = option
                st.session_state[nonce_key] += 1
                st.rerun()

        if not locked and selected_option:
            speak_nepali(selected_option, nonce=st.session_state[nonce_key])

        if not locked and st.button("Check", key=f"check_{lesson_id}_{pos}", disabled=selected_option is None):
            from bindu.domain.exercise_validator import check_multiple_choice
            correct = check_multiple_choice(selected_option, exercise.answer)
            submitted = True
            result = {"selected": selected_option}
           
            st.session_state.pop(choice_key, None)
            st.session_state.pop(nonce_key, None)

    elif exercise.type == ExerciseType.WORD_BANK:
        st.caption("Tap the tokens below in the correct order (each tap also speaks it):")
        order_key = f"wb_order_{lesson_id}_{pos}"
        tok_nonce_key = f"wb_speak_nonce_{lesson_id}_{pos}"
        tok_last_key = f"wb_speak_last_{lesson_id}_{pos}"
        st.session_state.setdefault(order_key, [])
        st.session_state.setdefault(tok_nonce_key, 0)

        chosen_indices = pending_feedback["selected_indices"] if locked else st.session_state[order_key]


        chosen_text = " ".join(exercise.tokens[i] for i in chosen_indices)

        placeholder_html = '<span style="opacity:0.5;">tap tokens below…</span>'
        st.markdown(
            f"<div style='min-height:2.4em;font-size:1.05rem;'>"
            f"{chosen_text or placeholder_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

 
        token_cols = st.columns(len(exercise.tokens))
        for tok_idx, col in enumerate(token_cols):
            with col:
                used = tok_idx in chosen_indices
                if locked:
                    st.button(
                        exercise.tokens[tok_idx],
                        key=f"tok_{lesson_id}_{pos}_{tok_idx}",
                        disabled=True,
                        use_container_width=True,
                    )
                elif st.button(
                    exercise.tokens[tok_idx],
                    key=f"tok_{lesson_id}_{pos}_{tok_idx}",
                    disabled=used,
                    use_container_width=True,
                ):
                    st.session_state[order_key].append(tok_idx)
                    st.session_state[tok_last_key] = exercise.tokens[tok_idx]
                    st.session_state[tok_nonce_key] += 1
                    st.rerun()

       
        if not locked and st.session_state.get(tok_last_key):
            speak_nepali(st.session_state[tok_last_key], nonce=st.session_state[tok_nonce_key])

        if not locked:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Reset order", key=f"reset_{lesson_id}_{pos}"):
                    st.session_state[order_key] = []
                    st.session_state.pop(tok_last_key, None)
                    st.rerun()
            with col_b:
                if st.button("Check", key=f"check_{lesson_id}_{pos}",
                             disabled=len(st.session_state[order_key]) != len(exercise.tokens)):
                    from bindu.domain.exercise_validator import check_word_bank
                    ordered_tokens = [exercise.tokens[i] for i in st.session_state[order_key]]
                    correct = check_word_bank(ordered_tokens, exercise.answer)
                    submitted = True
                    result = {"selected_indices": list(st.session_state[order_key])}
                    st.session_state.pop(order_key, None)
                    st.session_state.pop(tok_last_key, None)
                    st.session_state.pop(tok_nonce_key, None)

    if submitted:

        is_first_attempt = st.session_state[attempts_key].get(exercise_idx, 0) == 0
        st.session_state[attempts_key][exercise_idx] = st.session_state[attempts_key].get(exercise_idx, 0) + 1
        if correct:
            st.session_state[correct_set_key].add(exercise_idx)
            if is_first_attempt:
                st.session_state[first_try_key].add(exercise_idx)
        else:
            st.session_state[hearts_key] -= 1

            progress_repo.deduct_heart(user_id)

            queue.append(exercise_idx)

        st.session_state[feedback_key] = {
            "correct": correct,
            "answer_text": " ".join(exercise.answer),
            **result,
        }
        st.rerun()


    if locked:
        if pending_feedback["correct"]:
            st.success("Correct! ")
        else:
            st.error(f"Not quite, correct answer: {pending_feedback['answer_text']}")
        if st.button("Continue", key=f"continue_q_{lesson_id}_{pos}", type="primary", use_container_width=True):
            st.session_state.pop(feedback_key, None)
            st.session_state[pos_key] += 1
            st.rerun()



def render_profile() -> None:
    st.header("Profile")
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


def main() -> None:
    inject_app_chrome()
    init_backend()

    if "auth_user" not in st.session_state:
        render_auth_gate()
        return

    section = st.session_state.get("section", "Path map")
    active_lesson_id = st.session_state.get("active_lesson_id")

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

    inject_app_chrome()
    st.error(
        "Something went wrong loading this page. Please try again — if it "
        "keeps happening, use the button below to reset and start fresh."
    )
    if st.button("Reload BINDU", key="fatal_error_reload"):

        keep = {"auth_user", "auth_display_name", "theme"}
        for k in list(st.session_state.keys()):
            if k not in keep:
                st.session_state.pop(k, None)
        st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception:

        logging.getLogger("bindu").exception("Unhandled error in BINDU")
        render_fatal_error()      