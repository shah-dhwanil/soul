"""Alembic environment for the API app.

The target metadata is the API models only, and `include_object` drops every
object outside the `api` schema, so autogenerate can never propose a change
to the agent schema that `apps/agent` owns.
"""

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from api.models import Base

_api_root = Path(__file__).resolve().parent.parent
load_dotenv(_api_root / ".env")
load_dotenv(_api_root.parent / "agent" / ".env")

API_SCHEMA = "api"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    """Reuse the agent's configured database URL."""
    try:
        from agent.config import get_settings

        return get_settings().database_url
    except Exception:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Expected an asyncpg URL such as "
                "postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require"
            )
        return url


config.set_main_option("sqlalchemy.url", _database_url())

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Only ever touch the `api` schema."""
    if type_ == "table":
        return getattr(object, "schema", None) == API_SCHEMA
    schema = getattr(object, "schema", None)
    if schema is not None and schema != API_SCHEMA:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        include_schemas=True,
        version_table_schema=API_SCHEMA,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # The version table lives in the `api` schema, so it has to exist before
    # alembic touches it. Commit it on its own: SQLAlchemy opens an implicit
    # transaction for the statement, and the DDL would otherwise roll back.
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {API_SCHEMA}"))
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        include_schemas=True,
        version_table_schema=API_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
