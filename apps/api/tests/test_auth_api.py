import pytest
from fastapi.testclient import TestClient

from api.repositories import FakeAccountRepo


@pytest.fixture
def client():
    from api.deps import get_account_repo
    from main import app

    repo = FakeAccountRepo()
    app.dependency_overrides[get_account_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def _register(client, email="a@b.co", password="correct horse"):
    resp = client.post(
        "/v1/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_register_creates_account_and_returns_tokens(client):
    body = _register(client)
    assert body["user_id"]
    assert body["email"] == "a@b.co"
    assert body["onboarded"] is False
    assert body["onboarding_step"] == 0
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]


def test_register_rejects_short_password(client):
    resp = client.post(
        "/v1/auth/register", json={"email": "a@b.co", "password": "short"}
    )
    assert resp.status_code == 422


def test_register_rejects_malformed_email(client):
    resp = client.post(
        "/v1/auth/register", json={"email": "not-an-email", "password": "correct horse"}
    )
    assert resp.status_code == 422


def test_register_normalizes_email(client):
    first = client.post(
        "/v1/auth/register", json={"email": " A@B.co ", "password": "correct horse"}
    )
    assert first.status_code == 201
    assert first.json()["email"] == "a@b.co"

    second = client.post(
        "/v1/auth/register", json={"email": "a@b.co", "password": "correct horse"}
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "email_exists"


def test_login_returns_tokens_for_valid_credentials(client):
    registered = _register(client)
    resp = client.post(
        "/v1/auth/login", json={"email": "a@b.co", "password": "correct horse"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == registered["user_id"]
    assert body["email"] == "a@b.co"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_same_error_for_unknown_email_and_wrong_password(client):
    _register(client)
    unknown = client.post(
        "/v1/auth/login", json={"email": "nobody@b.co", "password": "correct horse"}
    )
    wrong = client.post(
        "/v1/auth/login", json={"email": "a@b.co", "password": "wrong password"}
    )
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["detail"]["code"] == "invalid_credentials"
    assert unknown.json() == wrong.json()


def test_refresh_returns_new_access_token(client):
    registered = _register(client)
    resp = client.post(
        "/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert set(body) == {"access_token"}


def test_refresh_rejects_access_token(client):
    registered = _register(client)
    resp = client.post(
        "/v1/auth/refresh", json={"refresh_token": registered["access_token"]}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "invalid_refresh_token"


def test_me_returns_account(client):
    registered = _register(client)
    resp = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "user_id": registered["user_id"],
        "email": "a@b.co",
        "onboarded": False,
        "onboarding_step": 0,
    }


def test_complete_onboarding_sets_flag_and_step(client):
    registered = _register(client)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    resp = client.post("/v1/auth/complete-onboarding", headers=headers)
    assert resp.status_code == 204

    me = client.get("/v1/auth/me", headers=headers).json()
    assert me["onboarded"] is True
    assert me["onboarding_step"] == 4

    again = client.post("/v1/auth/complete-onboarding", headers=headers)
    assert again.status_code == 204
    me = client.get("/v1/auth/me", headers=headers).json()
    assert me["onboarded"] is True
    assert me["onboarding_step"] == 4
