from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.ai.base import AIError, AIProvider
from app.services.ai.factory import build_provider
from app.services.cultural_service import CulturalService


@lru_cache
def _cached_provider(settings_key: tuple) -> AIProvider:  # noqa: ARG001 - key only drives caching
    return build_provider(get_settings())


def get_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    key = (settings.ai_provider, settings.meta_api_base_url, settings.meta_model_name, bool(settings.meta_api_key),
           settings.meta_structured_output, settings.meta_reasoning_effort, settings.meta_max_output_tokens)
    try:
        return _cached_provider(key)
    except AIError:
        raise


def get_cultural_service(provider: AIProvider = Depends(get_provider)) -> CulturalService:
    return CulturalService(provider)
