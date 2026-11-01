from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.core.ratelimit import ai_rate_limit
from app.schemas.tts import TTSRequest
from app.services.tts.swar import SwarClient, TTSService

router = APIRouter(prefix="/tts", tags=["tts"])


def get_tts_service(settings: Annotated[Settings, Depends(get_settings)]) -> TTSService:
    return TTSService(SwarClient(settings), settings)


@router.post("", dependencies=[Depends(ai_rate_limit)], response_class=Response,
             responses={200: {"content": {"audio/wav": {}}}})
async def speak(body: TTSRequest, service: Annotated[TTSService, Depends(get_tts_service)],
                settings: Annotated[Settings, Depends(get_settings)]) -> Response:
    """Nepali text -> speech using the Swar model. Returns audio/wav. Identical requests are served from a cache."""
    if len(body.text) > settings.tts_max_chars:
        raise HTTPException(422, f"Text is over {settings.tts_max_chars} characters.")
    audio = await service.speak(body.text, body.quality or settings.swar_quality)
    return Response(audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"})
