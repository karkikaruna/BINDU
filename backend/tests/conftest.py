from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_provider
from app.core.config import Settings, get_settings
from app.core.ratelimit import limiter
from app.main import create_app
from app.services.ai.mock_provider import MockProvider


def make_settings(**kw) -> Settings:
    base = dict(app_env="development", ai_provider="mock", auth_mode="dev", meta_api_key="", max_upload_size_mb=1, ai_rate_limit_per_minute=100)
    base.update(kw)
    return Settings(_env_file=None, **base)


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()


@pytest.fixture
def make_client():
    """Factory so tests can choose settings/provider. Dependencies are overridden on a fresh app each time."""
    def _make(settings: Settings | None = None, provider=None) -> TestClient:
        s = settings or make_settings()
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: s
        app.dependency_overrides[get_provider] = lambda: provider or MockProvider()
        return TestClient(app)
    return _make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


def image_bytes(fmt: str = "PNG", size=(64, 48), color=(200, 120, 60), exif: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    kwargs = {"exif": exif} if exif and fmt == "JPEG" else {}
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()
