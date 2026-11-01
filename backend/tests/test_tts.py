from __future__ import annotations

import httpx
import pytest

from app.api.v1.tts import get_tts_service
from app.services.tts.swar import SwarClient, TTSService
from tests.conftest import make_settings

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32


def _app(make_client, tmp_path, handler, **kw):
    s = make_settings(swar_base_url="https://swar.test", swar_api_key="k", swar_voice_id="maya",
                      tts_cache_dir=str(tmp_path), **kw)
    client = make_client(s)
    svc = TTSService(SwarClient(s, transport=httpx.MockTransport(handler)), s)
    client.app.dependency_overrides[get_tts_service] = lambda: svc
    return client


def test_tts_returns_wav_and_caches(make_client, tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert req.headers["x-api-key"] == "k"
        assert req.url.path == "/tts"
        assert b"maya" in req.content and "नमस्ते".encode() in req.content
        return httpx.Response(200, content=WAV, headers={"content-type": "audio/wav"})

    c = _app(make_client, tmp_path, handler)
    for _ in range(2):
        r = c.post("/api/v1/tts", json={"text": "  नमस्ते  "})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content == WAV
    assert len(calls) == 1  # second request came from the disk cache


def test_picks_first_preset_when_no_voice_configured(make_client, tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/voices":
            return httpx.Response(200, json={"presets": ["aarav", "maya"], "enrolled": []})
        assert b"aarav" in req.content
        return httpx.Response(200, content=WAV)

    s = make_settings(swar_base_url="https://swar.test", swar_voice_id="", tts_cache_dir=str(tmp_path))
    c = make_client(s)
    svc = TTSService(SwarClient(s, transport=httpx.MockTransport(handler)), s)
    c.app.dependency_overrides[get_tts_service] = lambda: svc
    assert c.post("/api/v1/tts", json={"text": "धन्यवाद"}).status_code == 200


def test_not_configured_is_503(make_client, tmp_path):
    s = make_settings(swar_base_url="", tts_cache_dir=str(tmp_path))
    r = make_client(s).post("/api/v1/tts", json={"text": "नमस्ते"})
    assert r.status_code == 503 and r.json()["error"]["message"] == "AI is not configured on this server."


@pytest.mark.parametrize("body", [{"text": "   "}, {"text": ""}, {}, {"text": "x", "quality": "ultra"}])
def test_bad_input_is_422(make_client, tmp_path, body):
    c = _app(make_client, tmp_path, lambda r: httpx.Response(200, content=WAV))
    assert c.post("/api/v1/tts", json=body).status_code == 422


def test_text_too_long_is_422(make_client, tmp_path):
    c = _app(make_client, tmp_path, lambda r: httpx.Response(200, content=WAV), tts_max_chars=5)
    assert c.post("/api/v1/tts", json={"text": "नमस्ते हजुर"}).status_code == 422


def test_tunnel_down_is_503_and_nothing_cached(make_client, tmp_path):
    def handler(req):
        raise httpx.ConnectError("boom")

    c = _app(make_client, tmp_path, handler)
    assert c.post("/api/v1/tts", json={"text": "नमस्ते"}).status_code == 503
    assert not list(tmp_path.glob("*.wav"))


def test_timeout_is_504(make_client, tmp_path):
    def handler(req):
        raise httpx.ReadTimeout("slow")

    assert _app(make_client, tmp_path, handler).post("/api/v1/tts", json={"text": "नमस्ते"}).status_code == 504


def test_html_error_page_is_not_served_as_audio(make_client, tmp_path):
    c = _app(make_client, tmp_path, lambda r: httpx.Response(200, content=b"<html>cloudflare</html>"))
    r = c.post("/api/v1/tts", json={"text": "नमस्ते"})
    assert r.status_code == 502 and not list(tmp_path.glob("*.wav"))


def test_bad_api_key_does_not_leak_detail(make_client, tmp_path):
    c = _app(make_client, tmp_path, lambda r: httpx.Response(401, json={"detail": "bad or missing X-API-Key"}))
    r = c.post("/api/v1/tts", json={"text": "नमस्ते"})
    assert r.status_code == 503 and "X-API-Key" not in r.text


def test_rate_limited(make_client, tmp_path):
    c = _app(make_client, tmp_path, lambda r: httpx.Response(200, content=WAV), ai_rate_limit_per_minute=1)
    assert c.post("/api/v1/tts", json={"text": "क"}).status_code == 200
    assert c.post("/api/v1/tts", json={"text": "ख"}).status_code == 429
