"""Single source of truth for *what gets spoken* in the lesson player.

Both `build_lessons_json.py` (puts `prompt_ne` into lessons.json) and `generate_nepali_audio.py` (synthesises the audio)
import this, so the text the app asks to hear is always exactly the text that was pre-recorded.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES = json.loads((ROOT / "content" / "spoken_overrides.json").read_text(encoding="utf-8"))
OVERRIDES = {k: v for k, v in OVERRIDES.items() if not k.startswith("_")}
LATIN = re.compile(r"[A-Za-z]")


def norm(text: str) -> str:
    """Collapse whitespace exactly like the app does before it looks a clip up (lib/speech.ts)."""
    return " ".join(str(text).split())


def spoken(text: str) -> str:
    """Nepali text as it should be read: Latin words replaced by their Devanagari spelling."""
    out = norm(text)
    for word, nepali in OVERRIDES.items():
        out = re.sub(rf"\b{re.escape(word)}\b", nepali, out)
    return out


def options_of(ex: dict) -> list[str]:
    return ex.get("nepali_options") or ex.get("nepali_options_draft") or []


def tokens_of(ex: dict) -> list[str]:
    return ex.get("nepali_tokens") or ex.get("nepali_tokens_draft") or []


def answer_of(ex: dict) -> list[str]:
    return ex.get("nepali_answer") or ex.get("nepali_answer_draft") or []


def prompt_ne(ex: dict) -> str:
    return spoken(ex.get("nepali_prompt") or "")


def exercise_texts(ex: dict) -> list[tuple[str, str]]:
    """Every (kind, text) the lesson player can ask to hear for one exercise."""
    items: list[tuple[str, str]] = []
    if prompt_ne(ex):
        items.append(("question", prompt_ne(ex)))
    items += [("option", norm(o)) for o in options_of(ex)]
    items += [("word", norm(t)) for t in tokens_of(ex)]
    ans = [norm(a) for a in answer_of(ex)]
    if ans:
        items.append(("answer", " ".join(ans)))
        # word-ordering: the speaker button reads the sentence built so far, so cover the correct partial sentences too
        if ex.get("type") == "word_bank":
            items += [("partial", " ".join(ans[:n])) for n in range(2, len(ans))]
    return [(k, t) for k, t in items if t]


def all_texts(data: dict) -> dict[str, str]:
    """Unique text -> first kind it was seen as, in lesson order."""
    seen: dict[str, str] = {}
    for unit in data["units"]:
        for lesson in unit["lessons"]:
            for ex in lesson["exercises"]:
                for kind, text in exercise_texts(ex):
                    seen.setdefault(text, kind)
    return seen
