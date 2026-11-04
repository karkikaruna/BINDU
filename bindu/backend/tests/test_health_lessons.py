def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_lessons_list_matches_reused_content(client):
    units = client.get("/api/v1/lessons").json()
    assert [u["name"] for u in units] == ["Greetings", "Numbers & Shopping", "Food & Directions"]
    assert sum(len(u["lessons"]) for u in units) == 9
    assert all(l["exercise_count"] == 7 for u in units for l in u["lessons"])


def test_lesson_detail_and_404(client):
    lesson = client.get("/api/v1/lessons/1").json()
    assert lesson["name"] == "Hello & Goodbye" and len(lesson["exercises"]) == 7
    assert lesson["exercises"][0]["answer"] == ["नमस्ते"]
    r = client.get("/api/v1/lessons/999")
    assert r.status_code == 404 and r.json()["error"]["message"] == "Lesson not found"
    assert client.get("/api/v1/lessons/abc").status_code == 422
