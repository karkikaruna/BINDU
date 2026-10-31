from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_cultural_service
from app.core.config import Settings, get_settings
from app.core.ratelimit import ai_rate_limit
from app.schemas.explore import AnalyzeResponse, AskRequest, AskResponse
from app.services.cultural_service import CulturalService, prepare_image

router = APIRouter(prefix="/explore", tags=["explore"])


@router.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(ai_rate_limit)])
async def analyze(
    image: Annotated[UploadFile, File(description="JPEG, PNG or WebP photo")],
    service: Annotated[CulturalService, Depends(get_cultural_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    question: Annotated[str | None, Form(max_length=500)] = None,
    place_hint: Annotated[str | None, Form(max_length=120, description="Optional place name, used to look up curated notes")] = None,
) -> AnalyzeResponse:
    """Analyze a landmark photo. Guests are allowed; the photo is processed in memory and not stored."""
    raw = await image.read(settings.max_upload_bytes + 1)
    jpeg = prepare_image(raw, image.content_type, settings.max_upload_bytes)
    return await service.analyze(jpeg, (question or "").strip() or None, (place_hint or "").strip() or None)


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(ai_rate_limit)])
async def ask(body: AskRequest, service: Annotated[CulturalService, Depends(get_cultural_service)]) -> AskResponse:
    """Follow-up question about an earlier analysis (text context only)."""
    return await service.ask(body)
