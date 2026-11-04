# BINDU 🇳🇵
Explore Nepal. Understand its culture. Learn its language.


| Feature | What it does |
|---|---|
| **Learn Nepali** | 3 units / 9 lessons / 63 exercises, hearts, XP, streaks, stars, Nepali pronunciation audio |
| **Explore with AI** | Photograph a landmark → cultural analysis → follow-up questions → save → shareable postcard. Saved items live in the **My Journey** tab |
| **Ask BINDU** | Stateless culture / travel Q&A chat with follow-up chips |

## Run it

Backend (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env           
python -m pytest -q
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000     
```

Mobile (Node 20+):
```bash
cd mobile
npm ci --legacy-peer-deps
npm install --legacy-peer-deps
cp .env.example .env           
npx tsc --noEmit && npx jest
npx expo start -c  

             
```

## Deploy and build
- Backend: `docker build -t bindu-api backend && docker run -p 8000:8000 --env-file backend/.env bindu-api` (one worker, because the rate limiter is in-memory).
- Phone builds: `cd mobile && npx eas build --profile preview --platform android`. For a store build use HTTPS for `EXPO_PUBLIC_API_URL`.
- CI: `.github/workflows/ci.yml` runs backend tests, the typecheck and the mobile tests.

## Layout
`backend/` FastAPI (`app/services/ai/` provider layer) · `mobile/` Expo app · `content/` lesson YAML · `scripts/` lesson + audio tooling · `supabase/` migrations · `docs/api.md`.


