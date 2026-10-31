from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_trip_service
from app.core.ratelimit import ai_rate_limit
from app.schemas.trips import TripRequest, TripResponse
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/generate", response_model=TripResponse, dependencies=[Depends(ai_rate_limit)])
async def generate_trip(body: TripRequest, service: Annotated[TripService, Depends(get_trip_service)]) -> TripResponse:
    """Generate an itinerary. Nothing is stored server-side; the app saves the result on the device."""
    return await service.generate(body)
