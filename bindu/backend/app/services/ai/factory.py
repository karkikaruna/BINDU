from __future__ import annotations

from app.core.config import Settings
from app.services.ai.base import AIProvider
from app.services.ai.meta_provider import MetaProvider
from app.services.ai.mock_provider import MockProvider


def build_provider(settings: Settings) -> AIProvider:
    """Explicit selection only. A missing key with AI_PROVIDER=meta raises AINotConfiguredError (503), never mock."""
    if settings.ai_provider == "mock":
        return MockProvider()
    return MetaProvider(settings)
