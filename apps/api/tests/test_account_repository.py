import asyncio

from api.repositories import FakeAccountRepo


def test_account_repo_roundtrip():
    async def run():
        repo = FakeAccountRepo()
        await repo.create(email="a@b.co", password_hash="h", user_id="u1")
        assert (await repo.get_by_email("a@b.co"))["user_id"] == "u1"
        await repo.set_onboarded("u1")
        assert (await repo.get_by_user_id("u1"))["onboarded"] is True
        assert await repo.get_by_email("missing@b.co") is None

    asyncio.run(run())
