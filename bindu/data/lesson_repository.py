
from __future__ import annotations

import json

from bindu.data.local_cache import LocalCache
from bindu.data.supabase_client import get_client
from bindu.domain.models import Exercise, ExerciseType, Lesson, LessonUnit


class LessonRepository:
    def __init__(self, cache: LocalCache):
        self.cache = cache

    def refresh_from_remote(self) -> None:
        """Pulls units/lessons/exercises from Supabase into the local cache.
        Silently falls back to whatever's already cached if the request fails
        (offline, expired session, etc.) — mirrors the Kotlin behavior."""
        try:
            client = get_client()
            units = (
                client.table("units").select("*").order("order_index").execute().data
            )
            lessons = (
                client.table("lessons").select("*").order("order_index").execute().data
            )
            exercises = (
                client.table("exercises").select("*").order("order_index").execute().data
            )
            self.cache.replace_units(units)
            self.cache.replace_lessons(lessons)
            self.cache.replace_exercises(exercises)
        except Exception:
            pass

    def get_units(self) -> list[LessonUnit]:
        lessons_by_unit: dict[int, list[Lesson]] = {}
        for row in self.cache.get_lessons():
            lessons_by_unit.setdefault(row["unit_id"], []).append(
                Lesson(
                    id=row["id"], unit_id=row["unit_id"], name=row["name"],
                    order_index=row["order_index"],
                )
            )
        return [
            LessonUnit(
                id=row["id"], name=row["name"], order_index=row["order_index"],
                color_theme=row["color_theme"],
                lessons=lessons_by_unit.get(row["id"], []),
            )
            for row in self.cache.get_units()
        ]

    def get_exercises_for_lesson(self, lesson_id: int) -> list[Exercise]:
        exercises = []
        for row in self.cache.get_exercises_for_lesson(lesson_id):
            exercises.append(
                Exercise(
                    id=row["id"],
                    lesson_id=row["lesson_id"],
                    type=ExerciseType.WORD_BANK if row["type"] == "word_bank" else ExerciseType.MULTIPLE_CHOICE,
                    prompt=row["prompt"],
                    options=_parse_list(row["options_json"]),
                    tokens=_parse_list(row["tokens_json"]),
                    answer=_parse_list(row["answer_json"]),
                    audio_url=row["audio_url"],
                    order_index=row["order_index"],
                )
            )
        return exercises


def _parse_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return list(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return []
