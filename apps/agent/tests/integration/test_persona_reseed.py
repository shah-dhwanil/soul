from dataclasses import asdict

import pytest
from sqlalchemy import delete

from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.pg.models import UserPersona
from agent.repositories.persona import PersonaRepository

pytestmark = pytest.mark.integration

USER_ID = "reseed-test-user"


async def test_reseed_replaces_temperament_and_explicit_dials(session_factory):
    async with session_factory() as session:
        repo = PersonaRepository(session)
        await repo.get_or_create(USER_ID, temperament="wry")
        await session.commit()

        row = await repo.reseed(USER_ID, "steady")
        await session.commit()

        steady = asdict(TEMPERAMENTS["steady"].default_dials)
        assert row["temperament"] == "steady"
        assert row["dials"] == steady
        # The explicit dial overrides are dropped by the re-seed.
        assert "dials" not in row["settings"]

        stored = await repo.get(USER_ID)
        assert stored.temperament == "steady"
        assert stored.dials == steady
        assert "dials" not in stored.settings

        await session.execute(
            delete(UserPersona).where(UserPersona.user_id == USER_ID)
        )
        await session.commit()
