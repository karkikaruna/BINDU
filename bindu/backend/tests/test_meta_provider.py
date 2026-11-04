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


async def test_chat_and_card_parse_and_validate():
    from app.schemas.assistant import ChatMessage
    from app.schemas.cards import CardRequest

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


# ---------------------------------------------------------------- Muse Spark specifics / robustness

async def test_reasoning_effort_and_generous_token_budget_are_sent():
    seen = {}
    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(GOOD)))
    await run(provider(handler))
    assert seen["body"]["reasoning_effort"] == "low"
    assert seen["body"]["max_completion_tokens"] == 8000  # reasoning tokens count toward this cap


async def test_reasoning_effort_can_be_omitted():
    seen = {}
    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(GOOD)))
    await run(provider(handler, meta_reasoning_effort=""))
    assert "reasoning_effort" not in seen["body"]


async def test_structured_output_rejected_falls_back_to_prompt_only_json():
    bodies = []
    def handler(req):
        body = json.loads(req.content)
        bodies.append(body)
        if "response_format" in body:
            return httpx.Response(400, json={"error": {"message": "unsupported"}})
        return httpx.Response(200, json=completion(json.dumps(GOOD)))
    assert (await run(provider(handler))).title == "Carved window"
    assert len(bodies) == 2 and "response_format" in bodies[0] and "response_format" not in bodies[1]


async def test_malformed_output_is_retried_once_then_succeeds():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(200, json=completion("oops not json" if len(calls) == 1 else json.dumps(GOOD)))
    assert (await run(provider(handler))).title == "Carved window"
    assert len(calls) == 2


async def test_persistently_malformed_output_stops_after_one_retry():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(200, json=completion("still not json"))
    with pytest.raises(AIResponseError):
        await run(provider(handler))
    assert len(calls) == 2


async def test_reasoning_truncation_is_not_retried_and_is_a_clean_error():
    calls = []
    def handler(req):
        calls.append(1)
        return httpx.Response(200, json=completion(None, finish="length"))
    with pytest.raises(AIResponseError):
        await run(provider(handler))
    assert len(calls) == 1


def test_model_api_key_alias_is_accepted(monkeypatch):
    from app.core.config import Settings
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_API_KEY", "sk-from-meta-sdk-name")
    assert Settings(_env_file=None, ai_provider="meta").meta_api_key == "sk-from-meta-sdk-name"


def test_gemini_is_gone():
    import pytest as _pt
    from app.core.config import Settings
    with _pt.raises(Exception):
        Settings(_env_file=None, ai_provider="gemini")
    from app.services.ai import factory
    assert not hasattr(factory, "GeminiProvider")


# ---------------------------------------------------------------- the two features end to end over HTTP (Meta transport mocked)

def _meta_client(make_client, handler):
    s = make_settings(ai_provider="meta", meta_api_key="sk-test")
    return make_client(s, provider=MetaProvider(s, transport=httpx.MockTransport(handler)))


def test_explore_with_ai_end_to_end(make_client):
    from tests.conftest import image_bytes
    c = _meta_client(make_client, lambda r: httpx.Response(200, json=completion(json.dumps(GOOD))))
    r = c.post("/api/v1/explore/analyze", files={"image": ("a.png", image_bytes(), "image/png")}, data={"question": "What is this?"})
    assert r.status_code == 200
    j = r.json()
    assert j["provider"] == "meta" and j["model"] == "muse-spark-1.3" and j["is_mock"] is False
    assert j["analysis"]["title"] == "Carved window"
    assert j["analysis"]["cultural_context"]["needs_verification"] is True  # no curated match -> always flagged

    ask = {"answer": "Probably Newar craftsmen.", "confidence": "medium", "needs_verification": True}
    c2 = _meta_client(make_client, lambda r: httpx.Response(200, json=completion(json.dumps(ask))))
    r = c2.post("/api/v1/explore/ask", json={"question": "Who made it?", "context_title": "Window", "context_summary": "Carved timber"})
    assert r.status_code == 200 and r.json()["result"]["answer"].startswith("Probably") and r.json()["provider"] == "meta"


def test_ask_bindu_assistant_end_to_end(make_client):
    ans = {"answer": "Cover shoulders and knees; remove shoes at the entrance.", "confidence": "high", "needs_verification": False, "followups": ["What about photography?"]}
    seen = {}
    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=completion(json.dumps(ans)))
    c = _meta_client(make_client, handler)
    r = c.post("/api/v1/assistant/chat", json={"messages": [{"role": "user", "content": "What should I wear at a temple?"}]})
    assert r.status_code == 200
    j = r.json()
    assert j["provider"] == "meta" and j["is_mock"] is False and j["result"]["followups"] == ["What about photography?"]
    assert seen["body"]["messages"][0]["role"] == "developer" and seen["body"]["model"] == "muse-spark-1.3"


def test_ai_endpoints_return_503_not_mock_when_key_missing(make_client):
    from app.api.deps import get_provider
    from app.core.config import get_settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    s = make_settings(ai_provider="meta", meta_api_key="")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: s   # real get_provider -> build_provider -> AINotConfiguredError
    c = TestClient(app)
    for r in (
        c.post("/api/v1/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}),
        c.post("/api/v1/explore/ask", json={"question": "hi there"}),
    ):
        assert r.status_code == 503 and r.json()["error"]["message"] == "AI is not configured on this server."


# ---------------------------------------------------------------- tolerant parsing (Explore's schema is large and strict)

async def test_slightly_over_limit_output_is_trimmed_not_rejected():
    big = {**GOOD, "observations": [f"obs {i}" for i in range(10)], "related_places": [f"p{i}" for i in range(7)],
           "suggested_activities": ["a"] * 6, "cultural_context": {**GOOD["cultural_context"], "text": "x" * 2300}}
    r = await run(provider(lambda req: httpx.Response(200, json=completion(json.dumps(big)))))
    assert len(r.observations) == 8 and len(r.related_places) == 5 and len(r.suggested_activities) == 5
    assert len(r.cultural_context.text) == 2000


async def test_invalid_optional_phrase_is_dropped_but_analysis_survives():
    bad = {**GOOD, "phrase": {"nepali": "", "romanization": "", "english": "Hello"}}
    r = await run(provider(lambda req: httpx.Response(200, json=completion(json.dumps(bad)))))
    assert r.title == "Carved window" and r.phrase is None


async def test_missing_required_field_is_still_rejected():
    bad = {k: v for k, v in GOOD.items() if k != "observations"}
    with pytest.raises(AIResponseError):
        await run(provider(lambda req: httpx.Response(200, json=completion(json.dumps(bad)))))


async def test_null_optional_fields_are_fine():
    ok = {**GOOD, "identified_place": None, "phrase": None}
    r = await run(provider(lambda req: httpx.Response(200, json=completion(json.dumps(ok)))))
    assert r.identified_place is None and r.phrase is None
