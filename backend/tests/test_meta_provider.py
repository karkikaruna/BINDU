"""Meta provider tests run against a mocked HTTP transport. They verify our request shape against the
documented Chat Completions API and our error mapping; they do NOT prove behaviour of the live service."""
import base64
import json

import httpx
import pytest

from app.schemas.explore import CulturalAnalysis
from app.services.ai.base import (
    AINotConfiguredError, AIRateLimitedError, AIResponseError, AITimeoutError, AIUnavailableError,
)
from app.services.ai.meta_provider import MetaProvider, inline_schema
from tests.conftest import make_settings

GOOD = {
    "title": "Carved window", "observations": ["Dark timber frame", "Fine floral carving"],
    "identified_place": None, "identification_confidence": "low",
    "cultural_context": {"text": "Newar-style windows are often carved.", "confidence": "medium", "needs_verification": True},
    "related_places": ["Patan Museum"], "suggested_activities": [],
    "phrase": {"nepali": "यो राम्रो छ", "romanization": "Yo ramro cha", "english": "This is beautiful", "usage": ""},
}


def completion(content, finish="stop"):
    return {"id": "x", "object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish}]}


def provider(handler, **kw):
    s = make_settings(ai_provider="meta", meta_api_key="sk-test-123", **kw)
    return MetaProvider(s, transport=httpx.MockTransport(handler))


async def run(p):
    return await p.analyze_image(b"\xff\xd8jpegbytes", "What is this?", "NOTE: curated")


async def test_request_shape_matches_documented_api():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"], seen["auth"], seen["body"] = str(req.url), req.headers["authorization"], json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(GOOD)))

    result = await run(provider(handler))
    assert result.title == "Carved window"
    assert seen["url"] == "https://api.meta.ai/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test-123"
    b = seen["body"]
    assert b["model"] == "muse-spark-1.3" and b["max_completion_tokens"] > 0 and "max_tokens" not in b
    assert b["messages"][0]["role"] == "developer"
    user = b["messages"][1]
    assert user["role"] == "user"
    text_part, img_part = user["content"]
    assert text_part["type"] == "text" and "What is this?" in text_part["text"] and "NOTE: curated" in text_part["text"]
    assert img_part["type"] == "image_url"
    url = img_part["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,") and base64.b64decode(url.split(",", 1)[1]) == b"\xff\xd8jpegbytes"
    rf = b["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["name"] == "CulturalAnalysis"
    assert "$ref" not in json.dumps(rf) and "$defs" not in json.dumps(rf)


async def test_structured_output_can_be_disabled():
    seen = {}
    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(GOOD)))
    await run(provider(handler, meta_structured_output=False))
    assert "response_format" not in seen["body"]


async def test_json_in_code_fence_is_accepted():
    p = provider(lambda r: httpx.Response(200, json=completion("```json\n" + json.dumps(GOOD) + "\n```")))
    assert (await run(p)).observations[0] == "Dark timber frame"


@pytest.mark.parametrize("status,exc", [
    (429, AIRateLimitedError), (401, AINotConfiguredError), (403, AINotConfiguredError),
    (500, AIUnavailableError), (503, AIUnavailableError), (504, AITimeoutError), (400, AIResponseError),
])
async def test_http_errors_map_to_typed_errors(status, exc):
    with pytest.raises(exc):
        await run(provider(lambda r: httpx.Response(status, json={"error": {"message": "x"}})))


async def test_timeout_and_network_errors():
    def timeout(_): raise httpx.ReadTimeout("slow")
    def down(_): raise httpx.ConnectError("no route")
    with pytest.raises(AITimeoutError):
        await run(provider(timeout))
    with pytest.raises(AIUnavailableError):
        await run(provider(down))


@pytest.mark.parametrize("payload", [
    "not json at all",
    json.dumps({"title": "missing everything"}),
    json.dumps({**GOOD, "observations": []}),                                   # violates min_length
    json.dumps({**GOOD, "cultural_context": {**GOOD["cultural_context"], "confidence": "certain"}}),
    "",
])
async def test_invalid_model_output_is_rejected_not_shown(payload):
    with pytest.raises(AIResponseError):
        await run(provider(lambda r: httpx.Response(200, json=completion(payload))))


async def test_truncated_and_malformed_envelopes():
    with pytest.raises(AIResponseError):
        await run(provider(lambda r: httpx.Response(200, json=completion(json.dumps(GOOD), finish="length"))))
    with pytest.raises(AIResponseError):
        await run(provider(lambda r: httpx.Response(200, json={"choices": []})))
    with pytest.raises(AIResponseError):
        await run(provider(lambda r: httpx.Response(200, text="<html>gateway</html>")))


async def test_ask_follow_up():
    seen = {}
    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps({"answer": "Probably Newar craftsmen.", "confidence": "medium", "needs_verification": True})))
    r = await provider(handler).answer_question("Who made it?", "Window", "Carved timber")
    assert r.confidence == "medium"
    assert "Window" in seen["body"]["messages"][1]["content"] and "image_url" not in json.dumps(seen["body"])


def test_missing_key_refuses_to_build():
    with pytest.raises(AINotConfiguredError):
        MetaProvider(make_settings(ai_provider="meta", meta_api_key=""))


def _structured(payload):
    return lambda req: httpx.Response(200, json=completion(json.dumps(payload)))


async def test_itinerary_request_and_day_count_check():
    from app.schemas.trips import TripRequest

    good = {"title": "T", "summary": "S", "days": [{"day_number": 1, "title": "D1", "stops": [
        {"name": "Patan Durbar Square", "slot": "morning", "description": "x", "category": "", "tip": ""}]}], "tips": []}
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(good)))

    p = provider(handler)
    out = await p.generate_itinerary(TripRequest(destination="Patan", days=1, interests=["Local food"]), ["Patan Durbar Square"])
    assert out.days[0].stops[0].name == "Patan Durbar Square"
    user = seen["body"]["messages"][1]["content"]
    assert "Patan Durbar Square" in user and "Local food" in user
    assert seen["body"]["response_format"]["json_schema"]["name"] == "Itinerary"
    # Model returned 1 day but 2 were requested -> unusable, not silently accepted.
    with pytest.raises(AIResponseError):
        await provider(_structured(good)).generate_itinerary(TripRequest(destination="Patan", days=2), [])


async def test_practice_evaluate_chat_and_card_parse_and_validate():
    from app.schemas.assistant import ChatMessage
    from app.schemas.cards import CardRequest
    from app.schemas.practice import EvaluateRequest, PracticeRequest

    items = {"items": [{"prompt_en": f"p{i}", "expected_nepali": "नमस्ते", "romanization": "Namaste", "hint": ""} for i in range(5)]}
    out = await provider(_structured(items)).generate_language_practice(PracticeRequest(topic="greetings", count=2))
    assert len(out.items) == 2  # trimmed to the requested count

    ev = {"correct": True, "score": 90, "feedback": "Good", "corrected": ""}
    assert (await provider(_structured(ev)).evaluate_language_response(EvaluateRequest(prompt_en="Hi", expected_nepali="नमस्ते", user_answer="namaste"))).score == 90

    ans = {"answer": "Remove shoes.", "confidence": "high", "needs_verification": False, "followups": ["Why?"]}
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(ans)))

    reply = await provider(handler).chat([ChatMessage(role="user", content="Shoes at temples?"), ChatMessage(role="assistant", content="Depends."), ChatMessage(role="user", content="Hindu temple")])
    assert reply.followups == ["Why?"] and [m["role"] for m in seen["body"]["messages"]] == ["developer", "user", "assistant", "user"]

    card = {"headline": "Namaste", "caption": "A greeting.", "nepali": "नमस्ते", "romanization": "Namaste", "english": "Hello", "theme": "forest"}
    assert (await provider(_structured(card)).generate_visual_content(CardRequest(kind="phrase", title="Namaste"))).theme == "forest"
    with pytest.raises(AIResponseError):
        await provider(_structured({"headline": "x"})).generate_visual_content(CardRequest(kind="phrase", title="x"))


def test_inline_schema_is_flat_and_complete():
    s = inline_schema(CulturalAnalysis)
    assert "$defs" not in json.dumps(s) and s["properties"]["cultural_context"]["properties"]["confidence"]["enum"] == ["high", "medium", "low"]


def test_api_maps_provider_failures_to_safe_messages(make_client):
    from app.api.deps import get_provider
    from tests.conftest import image_bytes
    key = "sk-secret-key"
    s = make_settings(ai_provider="meta", meta_api_key=key)
    p = MetaProvider(s, transport=httpx.MockTransport(lambda r: httpx.Response(500, text=f"boom {key}")))
    c = make_client(s, provider=p)
    r = c.post("/api/v1/explore/analyze", files={"image": ("a.png", image_bytes(), "image/png")})
    assert r.status_code == 503 and key not in r.text
    assert r.json()["error"]["message"].startswith("The AI service is unavailable")
