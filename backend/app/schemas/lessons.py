from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ExerciseOut(BaseModel):
    id: int
    type: Literal["multiple_choice", "word_bank"]
    prompt: str
    options: list[str]
    tokens: list[str]
    answer: list[str]
    audio_url: str | None = None
    order_index: int


class LessonOut(BaseModel):
    id: int
    name: str
    order_index: int
    exercises: list[ExerciseOut]


class LessonSummary(BaseModel):
    id: int
    name: str
    order_index: int
    exercise_count: int


class UnitOut(BaseModel):
    id: int
    name: str
    order_index: int
    color_theme: str | None = None
    lessons: list[LessonSummary]
