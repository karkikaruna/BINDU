from __future__ import annotations

from app.core.config import Settings
from app.services.ai.base import AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.meta_provider import MetaProvider
from app.services.ai.mock_provider import MockProvider


def build_provider(settings: Settings) -> AIProvider:
    """Explicit selection only. A missing key with AI_PROVIDER=meta raises AINotConfiguredError (503), never mock."""
    if settings.ai_provider == "mock":
        return MockProvider()
    if settings.ai_provider == "gemini":
        return GeminiProvider(settings)
    return MetaProvider(settings)
