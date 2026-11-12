"""API-owned repositories.

Rows come back as plain dicts so routes never depend on the ORM shape, and
so tests can swap in `FakeAccountRepo` through `dependency_overrides`.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Account


def _row(account: Account) -> dict:
    return {
        "user_id": account.user_id,
        "email": account.email,
        "password_hash": account.password_hash,
        "onboarded": account.onboarded,
        "onboarding_step": account.onboarding_step,
        "created_at": account.created_at,
    }


class AccountRepository:
    """Reads and writes `api.accounts`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _account(self, user_id: str) -> Account | None:
        result = await self._session.execute(
            select(Account).where(Account.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> dict | None:
        result = await self._session.execute(
            select(Account).where(Account.email == email)
        )
        account = result.scalar_one_or_none()
        return _row(account) if account is not None else None

    async def get_by_user_id(self, user_id: str) -> dict | None:
        account = await self._account(user_id)
        return _row(account) if account is not None else None

    async def create(
        self, *, email: str, password_hash: str, user_id: str
    ) -> dict:
        account = Account(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            onboarded=False,
            onboarding_step=0,
        )
        self._session.add(account)
        await self._session.flush()
        return _row(account)

    async def set_onboarded(self, user_id: str) -> None:
        account = await self._account(user_id)
        if account is None:
            return
        account.onboarded = True
        account.onboarding_step = 4
        await self._session.flush()

    async def advance_onboarding_step(self, user_id: str, step: int) -> None:
        """Move the onboarding step forward. Never backward."""
        account = await self._account(user_id)
        if account is None:
            return
        if account.onboarding_step < step:
            account.onboarding_step = step
        await self._session.flush()


class FakeAccountRepo:
    """In-memory stand-in for AccountRepository, used by tests."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    async def get_by_email(self, email: str) -> dict | None:
        for row in self.rows.values():
            if row["email"] == email:
                return dict(row)
        return None

    async def get_by_user_id(self, user_id: str) -> dict | None:
        row = self.rows.get(user_id)
        return dict(row) if row is not None else None

    async def create(
        self, *, email: str, password_hash: str, user_id: str
    ) -> dict:
        if any(row["email"] == email for row in self.rows.values()):
            raise IntegrityError("insert into accounts", {}, Exception("duplicate key"))
        row = {
            "user_id": user_id,
            "email": email,
            "password_hash": password_hash,
            "onboarded": False,
            "onboarding_step": 0,
            "created_at": datetime.now(UTC),
        }
        self.rows[user_id] = row
        return dict(row)

    async def set_onboarded(self, user_id: str) -> None:
        row = self.rows.get(user_id)
        if row is None:
            return
        row["onboarded"] = True
        row["onboarding_step"] = 4

    async def advance_onboarding_step(self, user_id: str, step: int) -> None:
        row = self.rows.get(user_id)
        if row is None:
            return
        row["onboarding_step"] = max(row["onboarding_step"], step)
