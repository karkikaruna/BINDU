# BINDU API (implemented so far)

Base: `/api/v1`. Errors are always `{"error": {"code": <http status>, "message": "<safe text>"}}`. Interactive docs: `/docs`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | Status + configured AI provider |
| POST | `/explore/analyze` | optional (guest ok) | multipart: `image` (JPEG/PNG/WebP), `question?`, `place_hint?`. Rate limited. |
| POST | `/explore/ask` | optional | JSON `{question, context_title?, context_summary?}`. Text only; the photo is never re-sent. |
| GET | `/lessons` | none | Curriculum outline (reused from the original BINDU app) |
| GET | `/lessons/{id}` | none | Lesson with exercises |

`/explore/*` responses carry `provider`, `model` and `is_mock`. `is_mock=true` means the answer did NOT come from a model.

Status codes: 400 unreadable image, 401 bad/expired token, 413 too large, 415 wrong type, 422 invalid input,
429 rate limited (`Retry-After`), 501 unimplemented AI operation, 503 AI unavailable/not configured, 504 AI timeout.

| POST | `/trips/generate` | optional | `{destination, days 1-7, interests[], pace, budget}` → itinerary. Rate limited. |
| GET | `/places/nearby` | none | `lat, lng, radius_km?, category?, limit?` → curated places, closest first |
| GET | `/places/search` | none | `q, category?, limit?` |
| GET | `/places/categories` | none | Category names |
| POST | `/practice/generate` | optional | `{topic, level, count 1-5}` → phrase items. Rate limited. |
| POST | `/practice/evaluate` | optional | `{prompt_en, expected_nepali, user_answer}`; `method` is `exact` (no model) or `ai`. Rate limited. |
| POST | `/assistant/chat` | optional | `{messages[1-12]}`, last must be from the user. Stateless. Rate limited. |
| POST | `/cards/generate` | optional | `{kind, title, body?, nepali?, english?}` → postcard text. Rate limited. |

| DELETE | `/account` | **required** | Permanently deletes the signed-in user's account and all synced rows (uses the server-side service-role key; the user id comes from the verified token). 503 if not configured. |

Saved trips, discoveries and progress sync directly between the app and Supabase (RLS-protected); the API stores nothing.
