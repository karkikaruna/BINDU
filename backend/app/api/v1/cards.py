from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_provider
from app.core.ratelimit import ai_rate_limit
from app.schemas.cards import CardRequest, CardResponse
from app.services.ai.base import AIProvider

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("/generate", response_model=CardResponse, dependencies=[Depends(ai_rate_limit)])
async def generate(body: CardRequest, provider: Annotated[AIProvider, Depends(get_provider)]) -> CardResponse:
    """Text for a shareable postcard. The app renders the card itself."""
    card = await provider.generate_visual_content(body)
    return CardResponse(card=card, provider=provider.name, model=provider.model, is_mock=provider.is_mock)
