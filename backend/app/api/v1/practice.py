from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_practice_service
from app.core.ratelimit import ai_rate_limit
from app.schemas.practice import EvaluateRequest, EvaluateResponse, PracticeRequest, PracticeResponse
from app.services.practice_service import PracticeService

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/generate", response_model=PracticeResponse, dependencies=[Depends(ai_rate_limit)])
async def generate(body: PracticeRequest, service: Annotated[PracticeService, Depends(get_practice_service)]) -> PracticeResponse:
    return await service.generate(body)


@router.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(ai_rate_limit)])
async def evaluate(body: EvaluateRequest, service: Annotated[PracticeService, Depends(get_practice_service)]) -> EvaluateResponse:
    """Exact matches are answered locally; anything else is judged by the AI provider."""
    return await service.evaluate(body)
