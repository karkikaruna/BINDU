"""Trips, places, practice, assistant and cards, exercised through the HTTP API with the mock provider."""
from __future__ import annotations

from app.services import places_service
from app.services.practice_service import normalize

API = "/api/v1"


# ---- trips -----------------------------------------------------------------------------------------------
def test_trip_generation_shape_and_pace(client):
    r = client.post(f"{API}/trips/generate", json={"destination": "Kathmandu Valley", "days": 3, "pace": "relaxed", "interests": ["Local food"]})
    assert r.status_code == 200
    body = r.json()
    assert body["is_mock"] is True and "not included" in body["disclaimer"]
    days = body["itinerary"]["days"]
    assert [d["day_number"] for d in days] == [1, 2, 3]
    assert all(len(d["stops"]) == 2 for d in days)  # relaxed = 2 stops/day


def test_trip_uses_curated_places_as_grounding(client):
    names = {s["name"] for d in client.post(f"{API}/trips/generate", json={"destination": "Bhaktapur", "days": 1, "pace": "packed"}).json()["itinerary"]["days"] for s in d["stops"]}
    assert "Bhaktapur Durbar Square" in names


def test_trip_validation(client):
    for bad in ({"destination": "K", "days": 2}, {"destination": "Pokhara", "days": 0}, {"destination": "Pokhara", "days": 8}, {"destination": "Pokhara", "days": 2, "pace": "insane"}):
        assert client.post(f"{API}/trips/generate", json=bad).status_code == 422


def test_trip_rate_limited(make_client):
    from tests.conftest import make_settings
    c = make_client(make_settings(ai_rate_limit_per_minute=2))
    ok = [c.post(f"{API}/trips/generate", json={"destination": "Patan", "days": 1}).status_code for _ in range(3)]
    assert ok == [200, 200, 429]


# ---- places ----------------------------------------------------------------------------------------------
def test_nearby_sorted_by_distance_and_limited(client):
    # Standing in Patan Durbar Square: Patan first, Bhaktapur's sites last.
    body = client.get(f"{API}/places/nearby", params={"lat": 27.6727, "lng": 85.3253, "radius_km": 30}).json()
    names = [p["name"] for p in body["places"]]
    assert names[0] == "Patan Durbar Square" and body["places"][0]["distance_km"] < 0.1
    d = [p["distance_km"] for p in body["places"]]
    assert d == sorted(d)
    assert "live" in body["note"].lower() or "curated" in body["note"].lower()
    assert len(client.get(f"{API}/places/nearby", params={"lat": 27.7, "lng": 85.3, "limit": 3}).json()["places"]) == 3


def test_nearby_radius_and_category_filters(client):
    # Far from every curated place (western Nepal hills) and a small radius: nothing returned.
    far = client.get(f"{API}/places/nearby", params={"lat": 29.9, "lng": 81.0, "radius_km": 10}).json()
    assert far["places"] == []
    food = client.get(f"{API}/places/nearby", params={"lat": 27.67, "lng": 85.42, "category": "local food"}).json()["places"]
    assert food[0]["id"] == "juju-dhau-bhaktapur"
    assert all(p["category"] == "Local food" for p in food) and len(food) >= 3


def test_nearby_covers_pokhara_and_other_regions(client):
    pk = client.get(f"{API}/places/nearby", params={"lat": 28.2096, "lng": 83.9856, "radius_km": 10}).json()["places"]
    assert {"phewa-lake", "world-peace-pagoda", "pokhara-lakeside"} <= {p["id"] for p in pk}
    assert all(p["area"] == "Pokhara" for p in pk)
    lumbini = client.get(f"{API}/places/search", params={"q": "lumbini"}).json()["places"]
    assert lumbini[0]["source_url"].startswith("https://whc.unesco.org/")


def test_place_data_is_valid():
    ps = places_service._load()
    ids = [p["id"] for p in ps]
    assert len(ids) == len(set(ids)) and len(ps) >= 30
    for p in ps:
        assert 26 < p["latitude"] < 31 and 79 < p["longitude"] < 89, p["id"]  # inside Nepal's bounding box
        assert p["blurb"].strip() and p["category"].strip() and p["area"].strip()
        # A source is given only for UNESCO-listed claims; a url never appears without a name.
        assert (p.get("source_url") is None) == (p.get("source_name") is None)


def test_valley_trip_grounding_excludes_other_regions():
    valley = places_service.names_for_destination("Kathmandu Valley", limit=50)
    assert "Patan Durbar Square" in valley and "Phewa Lake" not in valley and "Lumbini (Maya Devi Temple)" not in valley
    assert "Phewa Lake" in places_service.names_for_destination("Pokhara")
    assert len(places_service.names_for_destination("Nepal", limit=50)) == len(places_service._load())


def test_nearby_rejects_bad_coordinates(client):
    assert client.get(f"{API}/places/nearby", params={"lat": 95, "lng": 0}).status_code == 422
    assert client.get(f"{API}/places/nearby", params={"lat": 0}).status_code == 422


def test_search_and_categories(client):
    assert {p["name"] for p in client.get(f"{API}/places/search", params={"q": "bhaktapur"}).json()["places"]} >= {"Bhaktapur Durbar Square", "Changu Narayan"}
    assert client.get(f"{API}/places/search", params={"q": "zzzz"}).json()["places"] == []
    assert "Local food" in client.get(f"{API}/places/categories").json()


def test_haversine_known_distance():
    # Kathmandu Durbar Square -> Patan Durbar Square is about 4 km (3.5 km north-south, 1.8 km east-west).
    assert 3.5 < places_service.haversine_km(27.7043, 85.3070, 27.6727, 85.3253) < 4.5
    assert places_service.haversine_km(10, 10, 10, 10) == 0


# ---- practice --------------------------------------------------------------------------------------------
def test_practice_generate(client):
    r = client.post(f"{API}/practice/generate", json={"topic": "greetings", "count": 3})
    assert r.status_code == 200 and len(r.json()["result"]["items"]) == 3 and r.json()["is_mock"] is True
    assert client.post(f"{API}/practice/generate", json={"topic": "x", "count": 9}).status_code == 422


def test_evaluate_exact_match_skips_the_model(client):
    r = client.post(f"{API}/practice/evaluate", json={"prompt_en": "Hello", "expected_nepali": "नमस्ते", "user_answer": " नमस्ते। "}).json()
    assert r["method"] == "exact" and r["result"]["correct"] and r["result"]["score"] == 100 and r["is_mock"] is False


def test_evaluate_wrong_answer_goes_to_provider(client):
    r = client.post(f"{API}/practice/evaluate", json={"prompt_en": "Thank you", "expected_nepali": "धन्यवाद", "user_answer": "नमस्ते"}).json()
    assert r["method"] == "ai" and r["result"]["correct"] is False and r["result"]["corrected"] == "धन्यवाद" and r["is_mock"] is True


def test_normalize_ignores_spacing_punctuation_and_case():
    assert normalize("यो  कति हो?") == normalize("योकति हो")
    assert normalize("Namaste!") == normalize("namaste")


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
