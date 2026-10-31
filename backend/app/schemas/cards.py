from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CardRequest(BaseModel):
    kind: Literal["discovery", "phrase", "place"]
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=1500)
    nepali: str = Field(default="", max_length=200)
    english: str = Field(default="", max_length=200)


class VisualCard(BaseModel):
    headline: str = Field(min_length=1, max_length=80)
    caption: str = Field(min_length=1, max_length=280)
    nepali: str = Field(default="", max_length=200)
    romanization: str = Field(default="", max_length=200)
    english: str = Field(default="", max_length=200)
    theme: Literal["forest", "terracotta", "himalaya", "marigold"] = "forest"


class CardResponse(BaseModel):
    card: VisualCard
    provider: str
    model: str
    is_mock: bool
