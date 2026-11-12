import pytest
from fastapi.testclient import TestClient


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




@pytest.fixture
def client():
    from api.deps import get_persona_repo
    from main import app

    repo = FakePersonaRepo()
    app.dependency_overrides[get_persona_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_temperaments_endpoint_lists_four_seeds(client):
    resp = client.get("/v1/onboarding/temperaments")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["temperaments"]) == 4
    assert all(t["first_line"] for t in body["temperaments"])


def test_create_user_requires_user_id_header(client):
    resp = client.post("/v1/users", json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"})
    assert resp.status_code == 400


def test_create_user_is_idempotent(client):
    headers = {"X-USER-ID": "u1"}
    payload = {"temperament": "steady", "locale": "en-US", "timezone": "UTC"}
    first = client.post("/v1/users", json=payload, headers=headers)
    second = client.post("/v1/users", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user_id"] == second.json()["user_id"]
    assert "dependency_level" not in first.json()


def test_path_and_header_user_id_must_match(client):
    resp = client.get("/v1/users/u1/traits", headers={"X-USER-ID": "u2"})
    assert resp.status_code == 400


def test_user_summary_never_exposes_stage_number(client):
    headers = {"X-USER-ID": "u1"}
    client.post("/v1/users", json={"temperament": "steady", "locale": "en-US", "timezone": "UTC"}, headers=headers)
    resp = client.get("/v1/users/u1", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "stage" not in body
    assert "dependency_level" not in body
    assert body["stage_permissions"]
