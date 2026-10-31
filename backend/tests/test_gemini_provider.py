"""Gemini provider tests use a mocked HTTP transport: they check request shape and error mapping only."""
import json

import httpx
import pytest

from app.services.ai.base import AINotConfiguredError, AIRateLimitedError, AIResponseError
from app.services.ai.factory import build_provider
from app.services.ai.gemini_provider import GeminiProvider
from tests.test_meta_provider import GOOD
from tests.conftest import make_settings


def reply(text, finish="STOP"):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": finish}]}


def provider(handler):
    s = make_settings(ai_provider="gemini", gemini_api_key="g-test")
    return GeminiProvider(s, transport=httpx.MockTransport(handler))


async def test_request_shape_and_parse():
    seen = {}

    def handler(req):
        seen["url"], seen["key"], seen["body"] = str(req.url), req.headers["x-goog-api-key"], json.loads(req.content)
        return httpx.Response(200, json=reply(json.dumps(GOOD)))

    r = await provider(handler).analyze_image(b"\xff\xd8jpeg", "What is this?", None)
    assert r.title == "Carved window"
    assert seen["url"].endswith("/models/gemini-2.5-flash:generateContent") and seen["key"] == "g-test"
    b = seen["body"]
    assert b["generationConfig"]["responseMimeType"] == "application/json"
    assert "JSON Schema" in b["systemInstruction"]["parts"][0]["text"]
    assert b["contents"][0]["role"] == "user"
    assert b["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/jpeg"


async def test_errors():
    with pytest.raises(AIRateLimitedError):
        await provider(lambda r: httpx.Response(429)).analyze_image(b"x", None, None)
    with pytest.raises(AIResponseError):
        await provider(lambda r: httpx.Response(200, json=reply("{}", "MAX_TOKENS"))).analyze_image(b"x", None, None)
    with pytest.raises(AIResponseError):
        await provider(lambda r: httpx.Response(200, json={"candidates": []})).analyze_image(b"x", None, None)


def test_missing_key_and_factory():
    with pytest.raises(AINotConfiguredError):
        build_provider(make_settings(ai_provider="gemini"))
    assert build_provider(make_settings(ai_provider="gemini", gemini_api_key="k")).name == "gemini"