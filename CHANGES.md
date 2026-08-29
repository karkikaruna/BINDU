# Changes in this update

## 1. Fixed unreadable question text on dark background
`render_question()` in `app.py` used `color:inherit` inside a
`components.html` iframe, which doesn't inherit Streamlit's theme — it
was resolving to black text, invisible against Streamlit's dark mode.
The question is now shown in its own card with a fixed Nepal-flag
(crimson → blue) gradient background and white text, so it stays
readable regardless of the app's light/dark theme.

## 2. Added login / signup (real accounts) + "Continue with Google"
- New `bindu/data/auth_repository.py` — salted SHA-256 password hashing,
  backed by a new `users` table in the local SQLite cache
  (`bindu/data/local_cache.py`) and mirrored in `supabase/schema.sql`.
- New `render_auth_gate()` in `app.py` — a Log in / Sign up screen shown
  before anything else. Replaces the old free-text "User ID" box (which
  let two people silently share/overwrite the same progress).
- **"Continue with Google"** button uses Streamlit's *native* OIDC login
  (`st.login()` / `st.logout()` / `st.user`, built into Streamlit 1.42+
  via Authlib) rather than a hand-rolled OAuth flow. It's wired to sync
  into the same `auth_user` / `auth_display_name` session keys the
  username/password flow uses, so the rest of the app doesn't care which
  method was used to sign in.
  - **You need to plug in your own Google OAuth credentials** for this
    to actually work — I can't generate those on your behalf. Steps are
    in `.streamlit/secrets.toml.example`:
    1. Create an OAuth 2.0 Client ID (Web application) at
       https://console.cloud.google.com/apis/credentials, with authorized
       redirect URI `http://localhost:8501/oauth2callback` (swap in your
       real domain once deployed).
    2. Paste the Client ID / Client secret into `.streamlit/secrets.toml`
       under `[auth]`, and set `cookie_secret` to a random string
       (`python -c "import secrets; print(secrets.token_hex(32))"`).
    3. `pip install -r requirements.txt` (adds `Authlib`, bumps
       `streamlit` to `>=1.42.0`).
  - Until you fill those in, clicking the button shows a friendly
    "not configured yet" warning instead of crashing — verified with
    Streamlit's `AppTest` headless test harness — and the
    username/password login underneath still works as a fallback.
- Progress, XP, hearts, and streak are tied to whichever identity signed
  in (username, or Google email if using Google). Sidebar shows a
  Namaste greeting + Log out button (calls `st.logout()` for Google
  sessions, so the Google cookie is cleared too).
- Note: username/password auth is local-only (fine for a course project
  / local-first app). If this ever runs against a shared Supabase
  backend for multiple real users, swap it for Supabase Auth —
  `supabase/schema.sql` already has the `auth.users`-linked tables
  scaffolded for that.

## 3. Nepali touches
- Namaste greeting on the login screen, sidebar, and profile page.
- Rotating Nepali proverbs (with English translation) on the path map.
- "साबास!" added to the lesson-complete message.
- 🏔️ icon + Nepal flag colors on the question card.

## 4. Hearts are now per-lesson (5 mistakes = lesson failed)
Previously, hearts were only a slow-refilling account-wide pool, and a
lesson passed/failed based on a 60%-correct ratio checked only after
every question had been shown.

Now each lesson **attempt** gets its own 5-heart budget
(`LESSON_HEARTS = 5`, matches `gamification.MAX_HEARTS`). Missing 5
questions ends that lesson attempt immediately — even mid-lesson — and
nothing is saved; the lesson stays locked/incomplete until retried.
Finishing all questions with at least 1 heart left = pass, with XP and
stars awarded. The account-wide hearts shown in the sidebar are still
deducted too (that's the slower daily-limit pool), but they're
independent of this per-lesson counter.

Verified with a standalone simulation (`simulate_lesson_flow.py`,
not part of the shipped app) against the real repositories:
- 5 mistakes → lesson fails, nothing saved (confirmed even when the
  5th mistake happens before the last question).
- 4 mistakes → lesson still passes.
- 2 mistakes → lesson passes, XP/stars saved correctly.

## 5. Every lesson now has exactly 7 questions
Some lessons only had 2-3 exercises, which made the 5-heart rule
meaningless (you can't miss 5 out of 3). `content/units.final.yaml` was
padded with new hand-authored multiple-choice / word-bank exercises
(Nepali script + English prompts, in the same style as the originals)
so all 9 lessons now have 7 questions each (63 total, up from 10).

Regenerate the local DB after editing content with:
```
python content/rebuild_content.py
```

## Not done / worth knowing
- Google sign-in needs real credentials from you (see section 2 above) —
  it's fully wired up in code but unusable until you add your own
  client_id/client_secret.
- Username/password auth is local-only (see note in #2) — no "forgot
  password" flow, no session persistence across browser refresh
  (Streamlit session state resets on reload, so logging back in is
  required after a hard refresh — Google sign-in is somewhat better
  here since Streamlit keeps its own auth cookie, but the app's local
  `auth_user` session key still needs `_sync_google_login()` to run
  again on reload, which it does automatically).
- The account-wide sidebar hearts and the new per-lesson hearts share
  the same `MAX_HEARTS = 5` cap by coincidence of reusing the constant;
  they're tracked completely separately in code.

## 6. Renamed the app/package from Yatra to BINDU
Every `yatra` reference (the `yatra/` package, its `bindu.*` imports,
`yatra_local.db`, docstrings, README/CHANGES prose) has been renamed to
`bindu`. The UI already showed "BINDU" as the product name — this makes
the code match it.

## 7. Dark theme is now the default, and Light mode is fixed
Previously the app defaulted to light and only *added* dark-specific CSS
on top when picked — light mode itself was never explicitly styled, it
just relied on Streamlit's native (light) base theme. That's what caused
the mismatched/broken UI: native widgets (buttons, inputs, popovers,
tabs, metrics) are compiled against whatever `[theme]` is set in
`.streamlit/config.toml` at *build* time, not swapped live, so anywhere
the custom CSS didn't reach, the old light base leaked through.

- `.streamlit/config.toml` now sets `base = "dark"` with matching dark
  colors, so native widgets are compiled dark from the first paint (no
  more flash-of-white / stray light-mode buttons or inputs).
- `get_theme()` now defaults to `"dark"` when no session preference is
  set.
- Added `LIGHT_THEME_CSS`, a full mirror of the existing
  `DARK_THEME_CSS`, so picking "Light" in Settings explicitly repaints
  every surface + text color back to light instead of assuming that's
  already the native default (which it no longer is). `inject_app_chrome()`
  now always applies one explicit theme layer or the other.
