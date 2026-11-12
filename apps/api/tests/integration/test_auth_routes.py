import os

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.errors import install_error_handler
from api.models import Account
from api.routes import auth

pytestmark = pytest.mark.integration

EMAIL = "auth-db-test@example.com"
PASSWORD = "correct horse battery staple"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set")
    return url


@pytest.mark.asyncio
async def test_auth_routes_work_against_the_real_accounts_table():
    url = _database_url()
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI()
    app.state.session_factory = session_factory
    install_error_handler(app)
    app.include_router(auth.router)
    transport = httpx.ASGITransport(app=app)
    try:
        async with session_factory() as session:
            await session.execute(
                Account.__table__.delete().where(Account.email == EMAIL)
            )
            await session.commit()
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            register = await client.post(
                "/v1/auth/register",
                json={"email": EMAIL, "password": PASSWORD},
            )
            assert register.status_code == 201, register.text
            body = register.json()
            assert body["email"] == EMAIL
            assert body["onboarded"] is False
            assert body["onboarding_step"] == 0
            assert body["access_token"]
            assert body["refresh_token"]

            duplicate = await client.post(
                "/v1/auth/register",
                json={"email": EMAIL, "password": PASSWORD},
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["code"] == "email_exists"

            login = await client.post(
                "/v1/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
            assert login.status_code == 200
            assert login.json()["user_id"] == body["user_id"]

            headers = {"Authorization": f"Bearer {body['access_token']}"}
            me = await client.get("/v1/auth/me", headers=headers)
            assert me.status_code == 200
            assert me.json()["user_id"] == body["user_id"]

            done = await client.post(
                "/v1/auth/complete-onboarding", headers=headers
            )
            assert done.status_code == 204
            me = await client.get("/v1/auth/me", headers=headers)
            assert me.json()["onboarded"] is True
            assert me.json()["onboarding_step"] == 4

            async with session_factory() as session:
                await session.execute(
                    Account.__table__.delete().where(Account.email == EMAIL)
                )
                await session.commit()
    finally:
        await engine.dispose()
