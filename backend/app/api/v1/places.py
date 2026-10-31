from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.places import NearbyResponse
from app.services import places_service

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/nearby", response_model=NearbyResponse)
def nearby(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_km: Annotated[float, Query(gt=0, le=500)] = 25,
    category: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> NearbyResponse:
    """Curated places near a point, closest first. The point is only used for this request and is not stored."""
    return NearbyResponse(places=places_service.nearby(lat, lng, radius_km, category, limit))


@router.get("/search", response_model=NearbyResponse)
def search(
    q: Annotated[str, Query(max_length=80)] = "",
    category: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> NearbyResponse:
    """Search by destination or place name when location is not shared."""
    return NearbyResponse(places=places_service.search(q, category, limit))


@router.get("/categories", response_model=list[str])
def categories() -> list[str]:
    return places_service.categories()
