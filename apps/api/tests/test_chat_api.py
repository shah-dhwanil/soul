from fastapi.testclient import TestClient

from tests.helpers import auth_headers


def test_chat_rejects_body_user_id():
    from main import app

    client = TestClient(app)
    resp = client.post(
        "/v1/chat",
        json={"user_id": "u1", "message": "hey"},
        headers=auth_headers("u1"),
    )
    assert resp.status_code == 422


def test_chat_rejects_whitespace_only_message():
    from main import app

    client = TestClient(app)
    resp = client.post("/v1/chat", json={"message": "   "}, headers=auth_headers("u1"))
    assert resp.status_code == 422
