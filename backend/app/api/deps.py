from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.ai.base import AIError, AIProvider
from app.services.ai.factory import build_provider
from app.services.cultural_service import CulturalService
from app.services.practice_service import PracticeService
from app.services.trip_service import TripService


@lru_cache
def _cached_provider(settings_key: tuple) -> AIProvider:  # noqa: ARG001 - key only drives caching
    return build_provider(get_settings())


def get_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    key = (settings.ai_provider, settings.meta_api_base_url, settings.meta_model_name, bool(settings.meta_api_key), settings.meta_structured_output,
           bool(settings.gemini_api_key), settings.gemini_model_name)
    try:
        return _cached_provider(key)
    except AIError:
        raise


def get_cultural_service(provider: AIProvider = Depends(get_provider)) -> CulturalService:
    return CulturalService(provider)


def get_trip_service(provider: AIProvider = Depends(get_provider)) -> TripService:
    return TripService(provider)


def get_practice_service(provider: AIProvider = Depends(get_provider)) -> PracticeService:
    return PracticeService(provider)
