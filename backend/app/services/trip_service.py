from __future__ import annotations

from app.schemas.trips import TripRequest, TripResponse
from app.services import places_service
from app.services.ai.base import AIProvider


class TripService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def generate(self, req: TripRequest) -> TripResponse:
        req = req.model_copy(update={"destination": req.destination.strip(), "interests": [i.strip() for i in req.interests if i.strip()]})
        known = places_service.names_for_destination(req.destination)
        itinerary = await self.provider.generate_itinerary(req, known)
        return TripResponse(itinerary=itinerary, provider=self.provider.name, model=self.provider.model, is_mock=self.provider.is_mock)
