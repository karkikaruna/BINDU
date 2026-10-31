from __future__ import annotations

from pydantic import BaseModel, Field


class PlaceOut(BaseModel):
    id: str
    name: str
    category: str
    area: str
    latitude: float
    longitude: float
    blurb: str
    distance_km: float | None = Field(default=None, description="Great-circle distance from the query point")
    source_name: str | None = None
    source_url: str | None = None


class NearbyResponse(BaseModel):
    places: list[PlaceOut]
    provider: str = "curated"
    note: str = (
        "Curated list of well-known sites with approximate coordinates. It is not a live map listing: "
        "no opening hours, prices or ratings are shown."
    )
