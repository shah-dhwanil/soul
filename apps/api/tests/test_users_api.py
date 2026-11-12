import pytest
from fastapi.testclient import TestClient

from agent.persona.constants.temperaments import TEMPERAMENTS
from api.repositories import FakeAccountRepo
from tests.helpers import auth_headers, expired_access_token

class FakePersonaRepo:
    """In-memory stand-in for PersonaRepository."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    async def get_or_create(self, user_id, *, temperament="steady", locale="en-US", timezone="UTC"):
        row = self.rows.get(user_id)
        if row is None:
            row = {
                "user_id": user_id,
                "temperament": temperament,
                "locale": locale,
                "timezone": timezone,
                "stage": 1,
                "dependency_level": 0,
                "dials": {},
                "learned_dials": {},
                "settings": {},
            }
            self.rows[user_id] = row
        return row

    async def get(self, user_id):
        return self.rows.get(user_id)

    async def list_traits(self, user_id, *, status=None):
        return []

    async def list_leanings(self, user_id, *, status=None):
        return []

    async def set_settings(self, user_id, settings):
        row = await self.get_or_create(user_id)
        row["settings"] = settings

    async def reseed(self, user_id, temperament):
        from dataclasses import asdict

        row = await self.get_or_create(user_id, temperament=temperament)
        dials = asdict(TEMPERAMENTS[temperament].default_dials)
        settings = dict(row.get("settings") or {})
        settings.pop("dials", None)
        row["temperament"] = temperament
        row["dials"] = dict(dials)
        row["settings"] = settings
        return row


@pytest.fixture
def persona_repo():
    return FakePersonaRepo()


@pytest.fixture
def account_repo():
    return FakeAccountRepo()


@pytest.fixture
def client(persona_repo, account_repo):
    from api.deps import get_account_repo, get_persona_repo
    from main import app

    app.dependency_overrides[get_persona_repo] = lambda: persona_repo
    app.dependency_overrides[get_account_repo] = lambda: account_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_temperaments_endpoint_lists_four_seeds(client):
    resp = client.get("/v1/onboarding/temperaments")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["temperaments"]) == 4
    assert all(t["first_line"] for t in body["temperaments"])


def test_create_user_requires_bearer_token(client):
    resp = client.post("/v1/users", json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "missing_token"


def test_missing_bearer_token_gets_401(client):
    resp = client.get("/v1/users/u1/traits")
    assert resp.status_code == 401
    assert resp.json()["code"] == "missing_token"


def test_x_user_id_header_alone_is_rejected(client):
    resp = client.get("/v1/users/u1/traits", headers={"X-USER-ID": "u1"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "missing_token"


def test_expired_access_token_gets_invalid_token(client):
    resp = client.get(
        "/v1/users/u1/traits", headers={"Authorization": expired_access_token("u1")}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"


def test_create_user_is_idempotent(client):
    headers = auth_headers("u1")
    payload = {"temperament": "steady", "locale": "en-US", "timezone": "UTC"}
    first = client.post("/v1/users", json=payload, headers=headers)
    second = client.post("/v1/users", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user_id"] == second.json()["user_id"]
    assert "dependency_level" not in first.json()


def test_path_and_header_user_id_must_match(client):
    resp = client.get("/v1/users/u1/traits", headers=auth_headers("u2"))
    assert resp.status_code == 400


def test_user_summary_never_exposes_stage_number(client):
    headers = auth_headers("u1")
    client.post("/v1/users", json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"}, headers=headers)
    resp = client.get("/v1/users/u1", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "stage" not in body
    assert "dependency_level" not in body
    assert body["stage_permissions"]


def _registered(client, email="a@b.co"):
    resp = client.post(
        "/v1/auth/register", json={"email": email, "password": "correct horse"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_temperament_patch_reseeds_persona(client, persona_repo):
    from dataclasses import asdict

    from agent.services.persona_state import _resolve_dials

    headers = auth_headers("u1")
    client.post(
        "/v1/users",
        json={"temperament": "wry", "locale": "en-US", "timezone": "UTC"},
        headers=headers,
    )
    # The user tunes a dial before re-picking a temperament.
    client.patch(
        "/v1/users/u1/settings", json={"warmth": 8}, headers=headers
    )

    resp = client.patch(
        "/v1/users/u1/temperament",
        json={"temperament": "steady"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"temperament": "steady"}

    row = persona_repo.rows["u1"]
    steady = asdict(TEMPERAMENTS["steady"].default_dials)
    assert row["temperament"] == "steady"
    assert row["dials"] == steady
    # The user's explicit dial overrides do not survive the re-seed, so the
    # dials are the new temperament's defaults.
    assert "dials" not in row["settings"]

    # The settings view and the dials Wren actually runs with agree.
    runtime = _resolve_dials(
        TEMPERAMENTS["steady"], row["dials"], row["learned_dials"]
    )
    effective = client.get("/v1/users/u1/settings", headers=headers).json()[
        "effective"
    ]
    for name in ("formality", "warmth", "directness", "humor", "initiative"):
        assert effective[name] == getattr(runtime, name)


def test_temperament_patch_rejects_unknown_id(client):
    resp = client.patch(
        "/v1/users/u1/temperament",
        json={"temperament": "chaotic"},
        headers=auth_headers("u1"),
    )
    assert resp.status_code == 422


def test_post_users_advances_onboarding_step(client):
    account = _registered(client)
    headers = auth_headers(account["user_id"])
    assert client.get("/v1/auth/me", headers=headers).json()["onboarding_step"] == 0

    resp = client.post(
        "/v1/users",
        json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"},
        headers=headers,
    )
    assert resp.status_code == 200
    after = client.get("/v1/auth/me", headers=headers).json()
    assert after["onboarding_step"] >= 1


def test_settings_patch_advances_step_for_name_and_dials(client):
    account = _registered(client)
    headers = auth_headers(account["user_id"])
    client.post(
        "/v1/users",
        json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"},
        headers=headers,
    )

    named = client.patch(
        f"/v1/users/{account['user_id']}/settings",
        json={"address": "Sam"},
        headers=headers,
    )
    assert named.status_code == 200
    step = client.get("/v1/auth/me", headers=headers).json()["onboarding_step"]
    assert step >= 2

    tuned = client.patch(
        f"/v1/users/{account['user_id']}/settings",
        json={"warmth": 7},
        headers=headers,
    )
    assert tuned.status_code == 200
    step = client.get("/v1/auth/me", headers=headers).json()["onboarding_step"]
    assert step >= 3
