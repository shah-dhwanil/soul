from fastapi.testclient import TestClient


def test_chat_rejects_body_user_id():
    from main import app

    client = TestClient(app)
    resp = client.post(
        "/v1/chat",
        json={"user_id": "u1", "message": "hey"},
        headers={"X-USER-ID": "u1"},
    )
    assert resp.status_code == 422


def test_chat_rejects_whitespace_only_message():
    from main import app

    client = TestClient(app)
    resp = client.post("/v1/chat", json={"message": "   "}, headers={"X-USER-ID": "u1"})
    assert resp.status_code == 422
