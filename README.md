# BINDU — Nepali Trainer for Travelers (Streamlit edition)

A Duolingo-style Nepali trainer: 3 units, 9 lessons, hearts/XP/streaks,
prayer-flag themed path map. Originally an Android/Kotlin app; this
version drops the Android/Compose layer entirely and runs as a single
Python app — **the internal logic is the product**, the Streamlit UI is
just a thin front end over it.

## Why this structure

The old README's core claim was that domain logic should be pure,
dependency-free, and independently testable. That didn't change — it's
just Python now instead of Kotlin:

```
bindu/
├── domain/                    # pure logic, zero I/O, zero framework imports
│   ├── models.py              # Exercise / Lesson / LessonUnit / UserStats
│   ├── gamification.py        # hearts / XP / streak rules
│   └── exercise_validator.py  # answer checking (multiple-choice, word-bank, fuzzy)
├── data/                      # I/O layer — the only place that touches SQLite/Supabase
│   ├── local_cache.py         # SQLite cache (replaces Room) — offline-first
│   ├── supabase_client.py     # single shared Supabase client
│   ├── lesson_repository.py   # curriculum: Supabase → cache → domain objects
│   └── progress_repository.py # hearts/XP/streak/progress: cache-first, sync-to-Supabase
tests/
├── test_gamification.py       # ported 1:1 from GamificationTest.kt
└── test_exercise_validator.py # ported 1:1 from ExerciseValidatorTest.kt
app.py                         # Streamlit UI — renders state, calls the layers above
content/                       # unchanged: units.yaml + seed_supabase.py
scripts/                       # offline Google-Translate/TTS content generation
supabase/schema.sql            # unchanged: same Postgres schema
```

`domain/` has no imports from `data/`, Streamlit, or Supabase — you can run
`pytest tests/` with nothing installed but `pytest` itself, exactly like
the original JUnit suite.

## What was removed

- The entire `app/` Android/Kotlin/Compose module (screens, ViewModels,
  Room DAOs/entities, WorkManager jobs, AndroidManifest, Gradle build).
- ExoPlayer (audio now plays via `st.audio` straight from the Supabase
  Storage URL) and Android notifications (no streak-reminder push in this
  version — see "Not yet ported" below).
- The Play Store release pipeline (`.github/workflows/release.yml`,
  signing config) — irrelevant once there's no `.aab` to ship.

## What's unchanged

- **Supabase schema** (`supabase/schema.sql`) — same tables, same RLS
  policies, same trigger.
- **Content pipeline shape** (`content/units.yaml`, `content/seed_supabase.py`,
  `scripts/generate_translations.py`, `scripts/generate_audio.py`) — still
  a separate offline Python process (English source → Nepali draft → human
  review → TTS audio → seed). The translation *engine* inside
  `generate_translations.py` was swapped from `facebook/nllb-200-distilled-600M`
  to Google Translate's public endpoint (called directly with `requests`,
  not through the `deep-translator` package — its `GoogleTranslator` wraps
  the same endpoint but its response parser is currently broken upstream)
  — NLLB was mistranslating short, idiomatic travel phrases, and this also
  drops the torch/transformers dependency entirely.
- **Business rules** — heart regen (4h/heart, cap 5), XP→level (100
  XP/level), streak increment/reset, and answer-checking are line-for-line
  ports of the Kotlin originals, with matching test cases.

## Setup

```bash
pip install -r requirements.txt

cp .env.example .env                          # for content/ scripts (python-dotenv)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # for the app itself
# fill in SUPABASE_URL / SUPABASE_ANON_KEY (and SERVICE_ROLE_KEY for seeding)
```

Run the Supabase schema once (`supabase/schema.sql` in the SQL editor),
then seed the curriculum:

```bash
python content/seed_supabase.py
```

Then run the app:

```bash
streamlit run app.py
```

## Testing

```bash
pytest tests/ -v
```

## Not yet ported (flag if you need these)

- **Auth**: the app currently uses a plain text-entered user ID
  (`st.session_state.user_id`) instead of real Supabase Auth
  login/session handling. Wiring up `supabase.auth.sign_in_with_password`
  is straightforward to add to `supabase_client.py` when you want it.
- **Streak-reminder notifications**: `StreakReminderWorker`/`HeartRefillWorker`
  were periodic Android background jobs; there's no server-side scheduler
  here. If you want reminders, the logic to reuse is already in
  `gamification.should_remind_streak()` — it just needs a cron (e.g. a
  scheduled GitHub Action calling a small script) instead of WorkManager.
- **Drag-and-drop word-bank UI**: Streamlit doesn't have native drag
  gestures, so word-bank exercises use tap-to-append-token buttons instead
  of the original `pointerInput`/`detectDragGestures` drag tiles. Same
  validation logic (`exercise_validator.check_word_bank`) either way.
