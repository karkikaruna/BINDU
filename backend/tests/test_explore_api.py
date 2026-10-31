import io
import struct

from PIL import Image

from app.services.cultural_service import find_curated, prepare_image
from tests.conftest import image_bytes, make_settings

URL = "/api/v1/explore/analyze"


def post(client, data=None, content_type="image/png", fields=None, headers=None):
    data = image_bytes() if data is None else data
    return client.post(URL, files={"image": ("photo.png", data, content_type)}, data=fields or {}, headers=headers or {})


def test_guest_analyze_with_mock_is_labelled_mock(client):
    r = post(client)
    assert r.status_code == 200
    body = r.json()
    assert body["is_mock"] is True and body["provider"] == "mock"
    assert body["analysis"]["cultural_context"]["needs_verification"] is True
    assert body["sources"] == [] and "verify" in body["disclaimer"].lower()


def test_curated_hint_adds_sources_and_notes(client):
    body = post(client, fields={"place_hint": "Patan Durbar Square"}).json()
    assert body["sources"][0]["url"] == "https://whc.unesco.org/en/list/121"
    assert "Curated notes were available" in body["analysis"]["cultural_context"]["text"]


def test_find_curated_whole_word_matching():
    assert find_curated("what is this at boudha?")["id"] == "boudhanath"
    assert find_curated("patanjali yoga") is None  # 'patan' must not match inside another word
    assert find_curated(None, "") is None


def test_rejects_non_image_type(client):
    r = post(client, data=b"%PDF-1.4", content_type="application/pdf")
    assert r.status_code == 415 and "JPEG" in r.json()["error"]["message"]


def test_rejects_spoofed_content(client):
    r = post(client, data=b"<html>not an image</html>", content_type="image/jpeg")
    assert r.status_code == 400


def test_rejects_type_mismatch(client):
    r = post(client, data=image_bytes("PNG"), content_type="image/jpeg")
    assert r.status_code == 415


def test_rejects_empty_and_truncated(client):
    assert post(client, data=b"").status_code == 400
    assert post(client, data=image_bytes("PNG")[:40]).status_code == 400


def test_rejects_too_large(make_client):
    c = make_client(make_settings(max_upload_size_mb=1))
    big = image_bytes("PNG", size=(1500, 1500), color=(1, 2, 3))
    noisy = io.BytesIO()
    Image.effect_noise((1500, 1500), 90).convert("RGB").save(noisy, format="PNG")
    assert len(noisy.getvalue()) > 1024 * 1024
    r = post(c, data=noisy.getvalue())
    assert r.status_code == 413
    assert big  # small solid image is fine (compresses well)
    assert post(c, data=big).status_code == 200


def test_missing_file_is_422(client):
    r = client.post(URL, data={"question": "hi"})
    assert r.status_code == 422 and r.json()["error"]["code"] == 422


def test_question_too_long_rejected(client):
    assert post(client, fields={"question": "x" * 501}).status_code == 422


def test_prepare_image_normalises_and_strips_exif():
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    src = image_bytes("JPEG", size=(3000, 2000), exif=exif.tobytes())
    assert b"SecretCameraMaker" in src
    out = prepare_image(src, "image/jpeg", 10_000_000)
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and max(img.size) == 1568
    assert b"SecretCameraMaker" not in out


def test_prepare_image_decompression_bomb_guard():
    # Craft a PNG header claiming 50k x 50k pixels (> MAX_PIXELS) with tiny payload.
    import zlib
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 50000, 50000, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00")) + chunk(b"IEND", b"")
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        prepare_image(png, "image/png", 10_000_000)
    assert e.value.status_code == 400


def test_ask_validation_and_mock(client):
    ok = client.post("/api/v1/explore/ask", json={"question": "Who built it?", "context_title": "Temple"})
    assert ok.status_code == 200 and ok.json()["is_mock"] is True
    assert client.post("/api/v1/explore/ask", json={"question": "?"}).status_code == 422


def test_rate_limit(make_client):
    c = make_client(make_settings(ai_rate_limit_per_minute=2))
    codes = [post(c).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    r = post(c)
    assert r.status_code == 429 and "Retry-After" in r.headers
    # Different user has their own bucket
    assert post(c, headers={"Authorization": "Bearer dev-other"}).status_code == 200


def test_meta_selected_without_key_is_clear_503_not_mock(make_client):
    from app.api.deps import get_provider
    from app.services.ai.factory import build_provider
    from app.core.config import get_settings
    s = make_settings(ai_provider="meta", meta_api_key="")
    c = make_client(s)
    # use the real provider factory rather than the mock override
    c.app.dependency_overrides[get_provider] = lambda: build_provider(s)
    r = post(c)
    assert r.status_code == 503 and "not configured" in r.json()["error"]["message"].lower()
    assert get_settings  # imported for completeness
