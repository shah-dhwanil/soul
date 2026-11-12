"""API-owned ORM models.

These live in the `api` Postgres schema, separate from the `agent` schema that
`apps/agent` owns. The API never writes to agent tables, and the agent never
sees an Account row: it only ever sees the `user_id` string.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="api")


class Account(Base):
    """One sign-in record: an email, its argon2 hash, and onboarding state."""

    __tablename__ = "accounts"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    onboarded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    onboarding_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
