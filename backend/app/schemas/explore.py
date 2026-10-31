from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class NepaliPhrase(BaseModel):
    nepali: str = Field(min_length=1, max_length=200)
    romanization: str = Field(min_length=1, max_length=200)
    english: str = Field(min_length=1, max_length=200)
    usage: str = Field(default="", max_length=400)


class CulturalContext(BaseModel):
    text: str = Field(max_length=2000)
    confidence: Confidence
    # True whenever the claims are not backed by curated source material.
    needs_verification: bool = True


class CulturalAnalysis(BaseModel):
    """What the model must return. Observations (what is visible) are kept apart from cultural claims."""

    title: str = Field(min_length=1, max_length=120)
    observations: list[str] = Field(min_length=1, max_length=8)
    identified_place: str | None = Field(default=None, max_length=120)
    identification_confidence: Confidence = "low"
    cultural_context: CulturalContext
    related_places: list[str] = Field(default_factory=list, max_length=5)
    suggested_activities: list[str] = Field(default_factory=list, max_length=5)
    phrase: NepaliPhrase | None = None


class SourceRef(BaseModel):
    name: str
    url: str | None = None


class AnalyzeResponse(BaseModel):
    analysis: CulturalAnalysis
    sources: list[SourceRef] = Field(default_factory=list)
    provider: str = Field(description="'meta' or 'mock'. Mock output is NOT a real model response.")
    model: str
    is_mock: bool
    disclaimer: str = (
        "AI-generated from the photo. Cultural and historical details may be incomplete or wrong; "
        "verify with trusted local sources."
    )


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    # Text-only context from the earlier analysis; the image is not re-sent or stored.
    context_title: str = Field(default="", max_length=120)
    context_summary: str = Field(default="", max_length=2000)


class AskAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2500)
    confidence: Confidence = "medium"
    needs_verification: bool = True


class AskResponse(BaseModel):
    result: AskAnswer
    provider: str
    model: str
    is_mock: bool
