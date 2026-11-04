from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.schemas.lessons import LessonOut, LessonSummary, UnitOut

router = APIRouter(prefix="/lessons", tags=["lessons"])
DATA = Path(__file__).resolve().parent.parent.parent / "data" / "lessons.json"


@lru_cache
def _load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@router.get("", response_model=list[UnitOut])
def list_lessons() -> list[UnitOut]:
    """Curriculum outline (reused from the original BINDU app). Exercises are fetched per lesson."""
    return [
        UnitOut(
            id=u["id"], name=u["name"], order_index=u["order_index"], color_theme=u.get("color_theme"),
            lessons=[LessonSummary(id=l["id"], name=l["name"], order_index=l["order_index"], exercise_count=len(l["exercises"])) for l in u["lessons"]],
        )
        for u in _load()["units"]
    ]


@router.get("/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int) -> LessonOut:
    for unit in _load()["units"]:
        for lesson in unit["lessons"]:
            if lesson["id"] == lesson_id:
                return LessonOut(**lesson)
    raise HTTPException(404, "Lesson not found")
