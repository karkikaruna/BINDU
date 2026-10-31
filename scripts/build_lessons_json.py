"""Convert the reused BINDU lesson YAML into lessons.json.

Mirrors the original app's content/rebuild_content.py: the learner sees the
English prompt, while options / tokens / answer come from the Nepali variant.
Output goes to the backend (served by /api/v1/lessons) and to the mobile app
(bundled so lessons work offline, as in the original app).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "content" / "units.final.yaml"
OUTPUTS = [
    ROOT / "backend" / "app" / "data" / "lessons.json",
    ROOT / "mobile" / "assets" / "lessons.json",
]


def build() -> dict:
    data = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    units, lesson_id, exercise_id = [], 0, 0
    for u_idx, unit in enumerate(data["units"], start=1):
        lessons = []
        for lesson in unit["lessons"]:
            lesson_id += 1
            exercises = []
            for ex in lesson["exercises"]:
                exercise_id += 1
                exercises.append(
                    {
                        "id": exercise_id,
                        "type": ex["type"],
                        "prompt": ex["english_prompt"],
                        "options": ex.get("nepali_options") or ex.get("nepali_options_draft") or [],
                        "tokens": ex.get("nepali_tokens") or ex.get("nepali_tokens_draft") or [],
                        "answer": ex.get("nepali_answer") or ex.get("nepali_answer_draft") or [],
                        "audio_url": ex.get("audio_url"),
                        "order_index": ex["order_index"],
                    }
                )
            lessons.append(
                {
                    "id": lesson_id,
                    "name": lesson["name"],
                    "order_index": lesson["order_index"],
                    "exercises": sorted(exercises, key=lambda e: e["order_index"]),
                }
            )
        units.append(
            {
                "id": u_idx,
                "name": unit["name"],
                "order_index": unit["order_index"],
                "color_theme": unit.get("color_theme"),
                "lessons": sorted(lessons, key=lambda l: l["order_index"]),
            }
        )
    return {"units": sorted(units, key=lambda u: u["order_index"])}


if __name__ == "__main__":
    payload = build()
    for out in OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote", out)
    n = sum(len(l["exercises"]) for u in payload["units"] for l in u["lessons"])
    print(f"{len(payload['units'])} units, {n} exercises")
