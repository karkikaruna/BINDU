"""Live smoke test for the Meta Muse Spark connection. Run from the backend folder:

    python scripts/check_meta.py

Reads backend/.env (META_API_KEY etc.), then makes three small REAL calls, one per feature:
Ask BINDU (chat), Explore follow-up (ask) and Explore with AI (photo analysis, using a generated test image).
Costs a few cents at most. The key is never printed.
"""
from __future__ import annotations

import asyncio
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.schemas.assistant import ChatMessage  # noqa: E402
from app.services.ai.base import AIError  # noqa: E402
from app.services.ai.factory import build_provider  # noqa: E402


async def step(name: str, coro):
    t0 = time.perf_counter()
    try:
        out = await coro
    except AIError as exc:
        print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
        return False
    print(f"  ok    {name} ({time.perf_counter() - t0:.1f}s)")
    return out


async def main() -> int:
    s = get_settings()
    if s.ai_provider != "meta":
        print(f"AI_PROVIDER is '{s.ai_provider}', not 'meta'. Set AI_PROVIDER=meta in backend/.env.")
        return 1
    if not s.meta_api_key:
        print("META_API_KEY is empty. Create a key at https://dev.meta.ai and put it in backend/.env.")
        return 1
    p = build_provider(s)
    print(f"Meta Muse Spark check -> {s.meta_api_base_url}  model={p.model}  reasoning_effort={s.meta_reasoning_effort or '(default)'}")

    buf = io.BytesIO()
    Image.new("RGB", (320, 240), (150, 60, 30)).save(buf, "JPEG")

    results = [
        await step("Ask BINDU (chat)", p.chat([ChatMessage(role="user", content="What should I wear at a temple in Nepal?")])),
        await step("Explore follow-up (ask)", p.answer_question("What is a stupa?", "Boudhanath", "A large white stupa with painted eyes.")),
        await step("Explore with AI (photo analysis)", p.analyze_image(buf.getvalue(), None, None)),
    ]
    if all(r is not False for r in results):
        print("\nAll good: Explore with AI and Ask BINDU are talking to Meta Muse Spark.")
        print("Sample Ask BINDU answer:", results[0].answer[:160].replace("\n", " "))
        return 0
    print("\nSomething failed. 401/403 = bad key; 429 = rate limit; 'truncated' = raise META_MAX_OUTPUT_TOKENS.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
