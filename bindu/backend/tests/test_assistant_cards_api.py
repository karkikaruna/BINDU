"""Assistant and cards, exercised through the HTTP API with the mock provider."""
from __future__ import annotations

API = "/api/v1"


# ---- assistant & cards -----------------------------------------------------------------------------------
def test_assistant_chat(client):
    r = client.post(f"{API}/assistant/chat", json={"messages": [{"role": "user", "content": "What is dal bhat?"}]})
    assert r.status_code == 200 and "dal bhat" in r.json()["result"]["answer"] and r.json()["result"]["needs_verification"] is True


def test_assistant_validation(client):
    assert client.post(f"{API}/assistant/chat", json={"messages": []}).status_code == 422
    assert client.post(f"{API}/assistant/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}).status_code == 422
    assert client.post(f"{API}/assistant/chat", json={"messages": [{"role": "user", "content": "x" * 1001}]}).status_code == 422
    too_long = [{"role": "user", "content": "q"}] * 13
    assert client.post(f"{API}/assistant/chat", json={"messages": too_long}).status_code == 422


def test_card_generate(client):
    r = client.post(f"{API}/cards/generate", json={"kind": "phrase", "title": "Namaste", "nepali": "नमस्ते", "english": "Hello"})
    assert r.status_code == 200 and r.json()["card"]["nepali"] == "नमस्ते" and r.json()["is_mock"] is True
    assert client.post(f"{API}/cards/generate", json={"kind": "nope", "title": "x"}).status_code == 422
