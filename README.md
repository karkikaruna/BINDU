
# BINDU-Learn Nepali one point at a time

BINDU is a lightweight,-learning app for **Nepali**, built with [Streamlit]. It walks learners through bite-sized lessons, multiple-choice and word-bank exercises, organized into themed units (Greetings, Numbers & Shopping, Food & Directions, and more), with hearts, XP, levels, and streaks to keep practice fun.


## Features

-**Structured lessons**:units made of short, focused lessons you unlock in order
-**Two exercise types**: multiple choice and word-bank (tap-the-tiles) translation
-**Hearts**: you have 5 hearts per session; get an answer wrong and you lose one, then they slowly refill
-**XP & levels**: earn XP as you complete lessons and level up over time
-**Streaks**come:  back daily to keep your streak alive
-**Audio support** for pronunciation where available
-**Works fully offline**: accounts and progress are stored in a local SQLite database out of the box; no cloud account needed



## Installation

1. **Unzip and enter the project folder**

   ```bash
   unzip bindu.zip
   cd bindu/bindu
   ```

2. **(Recommended) Create a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```


## Running the app

From the `bindu/bindu` folder (the one containing `app.py`), run:

```bash
streamlit run app.py
```

Streamlit will start a local server and open BINDU in your browser, typically at **http://localhost:8501**.

## Using BINDU

1. **Create an account**: on first launch, sign up with a username (3–32 characters: letters, numbers, `.`, `_`, or `-`) and a password (4+ characters). Accounts are stored locally, so no email or internet connection is required.
2. **Pick a unit**: units appear on the home path in order; complete one to unlock the next.
3. **Work through lessons**: each lesson is a short sequence of exercises:
   - **Multiple choice**: pick the correct translation from a few options
   - **Word bank**: tap word tiles in the right order to build the translation
4. **Watch your hearts**: a wrong answer costs a heart. Run out and you'll need to wait for hearts to refill before continuing that lesson.
5. **Earn XP and level up**: finishing lessons earns XP; every 100 XP is a new level.
6. **Keep your streak**: practicing daily keeps your streak counter climbing.
7. **Check your profile**: the  Profile page shows your XP, level, hearts, and streak at a glance.

## cloud sync with Supabase



1. Create a free project at [supabase.com](https://supabase.com).
2. Run the schema in `supabase/schema.sql` against your project (SQL Editor in the Supabase dashboard works well).
3. Copy the example config and fill in your project's credentials:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Then edit `.streamlit/secrets.toml`:

   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_ANON_KEY = "your-anon-public-key"
   ```

   (Alternatively, copy `.env.example` to `.env` and set the same values if you're not using Streamlit secrets.)

4. Re-run `streamlit run app.py`: BINDU will pick up the credentials automatically.

## Project structure

```
bindu/
├── app.py                     # Main Streamlit app
├── bindu/
│   ├── data/                  # Local cache, Supabase client, repositories (auth, lessons, progress)
│   └── domain/                # Core logic: gamification, exercise validation, models
├── content/                   # Lesson content (units.yaml and variants) + content-generation scripts
├── scripts/                   # Translation & audio generation helpers
├── supabase/schema.sql        # Database schema for optional cloud sync
├── tests/                     # Unit tests
├── assets/                    # Logo, icons, images
├── requirements.txt
└── .streamlit/                # Streamlit theme + secrets template
```
