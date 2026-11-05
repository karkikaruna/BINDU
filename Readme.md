<div align="center">
           
# BINDU 

### Explore Nepal. Understand its culture. Learn its language.

</div>                                                                                                                                                                                             

---

## The Problem

Millions of people visit Nepal each year. They stand in front of centuries-old temples they can't identify, read signs they can't understand, and talk to locals they can't speak with. They go home with photos, but little understanding.

**BINDU** (बिन्दु, "a point") turns every point on a traveler's journey into a moment of understanding: what you're looking at, why it matters, and how to say something about it in Nepali.

---

## Features

| | Feature | What it does |
|---|---|---|
| 📸 | **Explore with AI** | Photograph a landmark and get a cultural analysis, ask follow-up questions, save it, and share it as a postcard. Saved items live in the **My Journey** tab. |
| 🗣️ | **Learn Nepali** | 3 units, 9 lessons and 63 exercises with hearts, XP, streaks, stars and native Nepali pronunciation audio. |
| 💬 | **Ask BINDU** | A stateless culture and travel Q&A assistant with follow-up suggestion chips. |
| 🗺️ | **My Journey** | Your saved discoveries and learning progress, synced across devices. |


## Tech Stack

| Layer | Technology |
|---|---|
| **Mobile** | Expo 58, React Native 0.88, React 19, expo-router, NativeWind (Tailwind), Zustand, TanStack Query, React Hook Form + Zod, Reanimated |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, httpx, Pillow, PyJWT |
| **AI** | Meta Model API: Muse Spark (`muse-spark-1.3`) |
| **Speech** | Swar (Nepali TTS) with a per-phrase disk cache, plus pre-generated lesson audio |
| **Data & Auth** | Supabase (Postgres, Auth, Storage) with Row Level Security |
| **DevOps** | Docker, GitHub Actions, EAS Build |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- A Meta Model API key from [dev.meta.ai](https://dev.meta.ai) (or run with `AI_PROVIDER=mock`)
- *(Optional)* A Supabase project for accounts and sync

### One command

```bash
chmod +x start.sh   # first time only
./start.sh          # backend + mobile
./start.sh backend  # backend only
./start.sh mobile   # mobile only
```

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then add your keys
python -m pytest -q         # run the tests
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


Verify your Meta connection with a live smoke test. It makes three small real calls (chat, follow-up and photo analysis) and never prints your key:

```bash
python scripts/check_meta.py
```

### Mobile

```bash
cd mobile
npm ci --legacy-peer-deps
cp .env.example .env
npx tsc --noEmit && npx jest   # typecheck + tests
npx expo start -c
```

Then press `i` (iOS simulator), `a` (Android emulator), `w` (web), or scan the QR code with Expo Go.

> 📱 **On a physical phone**, set `EXPO_PUBLIC_API_URL` to your computer's LAN IP (e.g. `http://192.168.1.20:8000/api/v1`), not `localhost`.

### Configuration

**`backend/.env`**

| Variable | Description |
|---|---|
| `AI_PROVIDER` | `meta` (Muse Spark) or `mock` (clearly labelled, for dev) |
| `META_API_KEY` | Your key from [dev.meta.ai](https://dev.meta.ai) |
| `META_MODEL_NAME` | Defaults to `muse-spark-1.3` |
| `META_REASONING_EFFORT` | `low` keeps answers fast |
| `META_MAX_OUTPUT_TOKENS` | Output cap (reasoning tokens count toward it) |
| `AUTH_MODE` | `dev` (accepts `Bearer dev-<n>`, development only) or `supabase` |
| `SUPABASE_URL` / `SUPABASE_JWT_SECRET` | For verifying Supabase tokens |
| `SUPABASE_SERVICE_ROLE_KEY` | **Server only.** Needed for `DELETE /account` |
| `SWAR_BASE_URL` | Swar TTS server. Leave empty to disable server-side TTS |
| `AI_RATE_LIMIT_PER_MINUTE` | Per-client AI rate limit |
| `MAX_UPLOAD_SIZE_MB` | Max photo size |

**`mobile/.env`**

| Variable | Description |
|---|---|
| `EXPO_PUBLIC_API_URL` | Backend URL |
| `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Leave empty to run as a guest |

>  Never commit `.env` files, and never put the Supabase service-role key in the mobile app.

### Database

Apply the migrations in `supabase/migrations/` (`0001_init.sql`, `0002_identity.sql`). They create `profiles`, `progress`, `discoveries` and `trips`, each protected by Row Level Security so users can only read and write their own rows.

---

##  API

Base path: `/api/v1`. Full reference in [`docs/api.md`](docs/api.md).

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | none | Status and configured AI provider |
| `GET` | `/lessons` | none | Curriculum outline |
| `GET` | `/lessons/{id}` | none | Lesson with exercises |
| `GET` | `/tts` | optional | Nepali text to `audio/wav` (cached per phrase) |
| `POST` | `/explore/analyze` | optional | Photo to cultural analysis (multipart) |
| `POST` | `/explore/ask` | optional | Text follow-up on an analysis |
| `POST` | `/assistant/chat` | optional | Stateless Ask BINDU chat |
| `POST` | `/cards/generate` | optional | Postcard headline and caption |
| `DELETE` | `/account` | **required** | Permanently delete the account and all data |

Errors always have the same shape: `{"error": {"code": 429, "message": "..."}}`. Rate-limited responses include `Retry-After`.

---

## Testing & CI

```bash
# Backend
cd backend && python -m pytest -q

# Mobile
cd mobile && npx tsc --noEmit && npx jest
```

The backend suite covers auth, lessons, the Explore API, the assistant and cards, TTS, account deletion, and the Meta provider (against a mocked HTTP transport). The mobile suite covers auth, game logic, i18n, networking, speech and lesson audio.

GitHub Actions (`.github/workflows/ci.yml`) runs backend tests, the TypeScript typecheck and the mobile tests on every push and pull request.

##  Project Structure

```
bindu/
├── backend/            FastAPI service
│   ├── app/
│   │   ├── api/v1/     Route handlers
│   │   ├── services/
│   │   │   ├── ai/     Provider layer (Meta Muse Spark + mock)
│   │   │   └── tts/    Swar Nepali TTS client
│   │   ├── schemas/    Pydantic request/response models
│   │   ├── core/       Config, auth, rate limiting
│   │   └── data/       Curated places + lesson data
│   ├── scripts/        check_meta.py (live smoke test)
│   └── tests/
├── mobile/             Expo React Native app
│   ├── app/            Screens (expo-router)
│   ├── components/     Shared UI
│   ├── lib/            Gamification, sync, speech, i18n
│   ├── stores/         Zustand state
│   └── __tests__/
├── content/            Lesson source (YAML) + spoken overrides
├── scripts/            Lesson build + Nepali audio generation/upload
├── supabase/           Database migrations
└── docs/               API reference
```



---

<div align="center">
 धन्यवाद for exploring BINDU.
</div>
