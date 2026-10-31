"""Nearby/destination lookup over a curated, coordinate-tagged list.

This is deliberately NOT a live maps provider: it has no hours, prices or ratings. A Google/Mapbox-backed
implementation can replace `PlacesService._all()` later without changing the API.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.schemas.places import PlaceOut

DATA = Path(__file__).resolve().parent.parent / "data" / "places.json"
EARTH_RADIUS_KM = 6371.0088
# Districts that make up "Kathmandu Valley" for trip grounding.
VALLEY_AREAS = {"kathmandu", "lalitpur", "bhaktapur", "kirtipur"}


@lru_cache
def _load() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["places"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def categories() -> list[str]:
    return sorted({p["category"] for p in _load()})


def nearby(lat: float, lng: float, radius_km: float, category: str | None, limit: int) -> list[PlaceOut]:
    out = []
    for p in _load():
        if category and p["category"].lower() != category.lower():
            continue
        d = haversine_km(lat, lng, p["latitude"], p["longitude"])
        if d <= radius_km:
            out.append(PlaceOut(**p, distance_km=round(d, 2)))
    out.sort(key=lambda x: x.distance_km or 0)
    return out[:limit]


def search(query: str, category: str | None, limit: int) -> list[PlaceOut]:
    q = query.strip().lower()
    out = []
    for p in _load():
        if category and p["category"].lower() != category.lower():
            continue
        if not q or q in p["name"].lower() or q in p["area"].lower() or q in p["blurb"].lower():
            out.append(PlaceOut(**p))
    return out[:limit]


def names_for_destination(destination: str, limit: int = 10) -> list[str]:
    """Curated place names relevant to a destination text (matches area/name; 'kathmandu valley' matches all)."""
    d = destination.strip().lower()
    valley_text = {"kathmandu valley", "valley", "kathmandu"}
    whole_country = {"nepal"}
    hits = []
    for p in _load():
        area, name = p["area"].lower(), p["name"].lower()
        in_valley = area in VALLEY_AREAS
        if d in whole_country or (d in valley_text and in_valley) or d in area or area in d or d in name:
            hits.append(p["name"])
    return hits[:limit]
