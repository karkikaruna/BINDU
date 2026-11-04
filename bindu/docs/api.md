# BINDU API

Base: `/api/v1`. Errors are always `{"error": {"code": <http status>, "message": "<safe text>"}}`. Interactive docs: `/docs`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | Status + configured AI provider (`meta` = Meta Muse Spark, or `mock`) |
| GET | `/lessons` | none | Curriculum outline |
| GET | `/lessons/{id}` | none | Lesson with exercises |
| GET | `/tts` | optional | `text=<nepali text>[&quality=fast\|best]` → `audio/wav` (Swar). Cached per phrase. Own rate limit (`TTS_RATE_LIMIT_PER_MINUTE`, default 60). |
| POST | `/explore/analyze` | optional (guest ok) | multipart: `image` (JPEG/PNG/WebP), `question?`, `place_hint?`. Rate limited. |
| POST | `/explore/ask` | optional | JSON `{question, context_title?, context_summary?}`. Text only; the photo is never re-sent. |
| POST | `/assistant/chat` | optional | `{messages[1-12]}`, last must be from the user. Stateless. Rate limited. |
| POST | `/cards/generate` | optional | `{kind, title, body?, nepali?, english?}` → postcard text. Rate limited. |
| DELETE | `/account` | **required** | Permanently deletes the signed-in user's account and all synced rows (server-side service-role key; user id comes from the verified token). 503 if not configured. |

AI responses carry `provider`, `model` and `is_mock`. `is_mock=true` means the answer did NOT come from a model.

Status codes: 400 unreadable image, 401 bad/expired token, 413 too large, 415 wrong type, 422 invalid input, 429 rate limited (`Retry-After`), 501 unimplemented AI operation, 503 AI unavailable/not configured, 504 AI timeout.

Saved discoveries and progress sync directly between the app and Supabase (RLS-protected); the API stores nothing.
