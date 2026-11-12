import asyncio
import os

import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Account
from api.repositories import AccountRepository

pytestmark = pytest.mark.integration

EMAIL = "account-repo-test@example.com"
USER_ID = "account-repo-test-user"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set")
    return url


def test_accounts_table_exists_and_repository_roundtrips():
    url = _database_url()

    async def run():
        engine = create_async_engine(url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                conn = await session.connection()
                names = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_table_names(
                        schema="api"
                    )
                )
                assert "accounts" in names

                repo = AccountRepository(session)
                await repo.create(
                    email=EMAIL, password_hash="h", user_id=USER_ID
                )
                await session.commit()

                row = await repo.get_by_email(EMAIL)
                assert row is not None
                assert row["user_id"] == USER_ID
                assert row["onboarded"] is False
                assert row["onboarding_step"] == 0

                await repo.set_onboarded(USER_ID)
                await session.commit()

                row = await repo.get_by_user_id(USER_ID)
                assert row["onboarded"] is True
                assert row["onboarding_step"] == 4

                await session.execute(
                    delete(Account).where(Account.user_id == USER_ID)
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(run())
