"""Run Alembic migrations (same as `alembic upgrade head` from apps/agent)."""

from pathlib import Path

from alembic import command
from alembic.config import Config


def upgrade_head() -> None:
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    command.upgrade(Config(str(alembic_ini)), "head")
