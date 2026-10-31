from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Pace = Literal["relaxed", "balanced", "packed"]
Budget = Literal["budget", "mid", "comfortable"]
Slot = Literal["morning", "afternoon", "evening"]


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=80)
    days: int = Field(ge=1, le=7)
    interests: list[str] = Field(default_factory=list, max_length=6)
    pace: Pace = "balanced"
    budget: Budget = "mid"


class Stop(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slot: Slot
    description: str = Field(max_length=400)
    category: str = Field(default="", max_length=40)
    tip: str = Field(default="", max_length=200)


class ItineraryDay(BaseModel):
    day_number: int = Field(ge=1, le=7)
    title: str = Field(min_length=1, max_length=100)
    stops: list[Stop] = Field(min_length=1, max_length=6)


class Itinerary(BaseModel):
    """What the model must return. No prices, opening hours or transport times: those are not verifiable here."""

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(max_length=500)
    days: list[ItineraryDay] = Field(min_length=1, max_length=7)
    tips: list[str] = Field(default_factory=list, max_length=6)


class TripResponse(BaseModel):
    itinerary: Itinerary
    provider: str
    model: str
    is_mock: bool
    disclaimer: str = (
        "AI-generated plan. Opening hours, prices and transport are not included because they were not verified; "
        "check them locally before you go."
    )
