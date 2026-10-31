from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["Beginner", "Intermediate", "Advanced"]


class PracticeRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=80)
    level: Level = "Beginner"
    count: int = Field(default=3, ge=1, le=5)


class PracticeItem(BaseModel):
    prompt_en: str = Field(min_length=1, max_length=200)
    expected_nepali: str = Field(min_length=1, max_length=200)
    romanization: str = Field(min_length=1, max_length=200)
    hint: str = Field(default="", max_length=200)


class PracticeSet(BaseModel):
    items: list[PracticeItem] = Field(min_length=1, max_length=5)


class PracticeResponse(BaseModel):
    result: PracticeSet
    provider: str
    model: str
    is_mock: bool


class EvaluateRequest(BaseModel):
    prompt_en: str = Field(min_length=1, max_length=200)
    expected_nepali: str = Field(min_length=1, max_length=200)
    user_answer: str = Field(min_length=1, max_length=200)


class Evaluation(BaseModel):
    correct: bool
    score: int = Field(ge=0, le=100)
    feedback: str = Field(max_length=500)
    corrected: str = Field(default="", max_length=200)


class EvaluateResponse(BaseModel):
    result: Evaluation
    # "exact" = matched the expected answer without calling a model; otherwise the provider judged it.
    method: Literal["exact", "ai"]
    provider: str
    model: str
    is_mock: bool
