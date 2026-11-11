"""conversation memory outbox, ingestion state, ingest jobs

Staging-only: drops the old job-shaped memory_outbox and recreates schema;
does not backfill jobs, ingestion state, or outbox from existing rows.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-11 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_type = postgresql.ENUM(
        "thread_closed",
        "idle_checkpoint",
        "user_batch",
        name="memoryingestjobtype",
        schema="agent",
    )
    job_type.create(op.get_bind(), checkfirst=True)

    job_status = postgresql.ENUM(
        "pending",
        "processing",
        "processed",
        "failed",
        "deferred",
        name="memoryingestjobstatus",
        schema="agent",
    )
    job_status.create(op.get_bind(), checkfirst=True)

    ingestion_status = postgresql.ENUM(
        "pending",
        "ingested",
        "failed",
        name="memoryingestionstatestatus",
        schema="agent",
    )
    ingestion_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "memory_ingest_job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "job_type",
            postgresql.ENUM(
                "thread_closed",
                "idle_checkpoint",
                "user_batch",
                name="memoryingestjobtype",
                schema="agent",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "processing",
                "processed",
                "failed",
                "deferred",
                name="memoryingestjobstatus",
                schema="agent",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("conversation_from_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_to_id", sa.Uuid(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("episode_uuid", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="agent",
    )
    op.create_index(
        "ix_memory_ingest_job_status_priority",
        "memory_ingest_job",
        ["status", "priority", "created_at"],
        schema="agent",
    )
    op.create_index(
        "uniq_memory_ingest_job_idempotency_active",
        "memory_ingest_job",
        ["idempotency_key"],
        unique=True,
        schema="agent",
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.create_index(
        "ix_memory_ingest_job_user_status",
        "memory_ingest_job",
        ["user_id", "status"],
        schema="agent",
    )

    op.create_table(
        "memory_ingestion_state",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "ingested",
                "failed",
                name="memoryingestionstatestatus",
                schema="agent",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("episode_uuid", sa.String(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("conversation_id"),
        schema="agent",
    )
    op.create_index(
        "ix_memory_ingestion_state_user_status",
        "memory_ingestion_state",
        ["user_id", "status"],
        schema="agent",
    )
    op.create_index(
        "ix_memory_ingestion_state_thread_status",
        "memory_ingestion_state",
        ["thread_id", "status"],
        schema="agent",
    )

    op.drop_index(
        "ix_memory_outbox_user_status", table_name="memory_outbox", schema="agent"
    )
    op.drop_index(
        "uniq_memory_outbox_idempotency_active",
        table_name="memory_outbox",
        schema="agent",
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.drop_index(
        "ix_memory_outbox_status_priority", table_name="memory_outbox", schema="agent"
    )
    op.drop_table("memory_outbox", schema="agent")

    op.create_table(
        "memory_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="agent",
    )
    op.create_index(
        "uniq_memory_outbox_conversation",
        "memory_outbox",
        ["conversation_id"],
        unique=True,
        schema="agent",
    )
    op.create_index(
        "ix_memory_outbox_user_created",
        "memory_outbox",
        ["user_id", "created_at"],
        schema="agent",
    )

    op.drop_column("thread", "ingested_through_conversation_id", schema="agent")

    postgresql.ENUM(name="memoryoutboxstatus", schema="agent").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="memoryoutboxjobtype", schema="agent").drop(
        op.get_bind(), checkfirst=True
    )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for conversation memory outbox")
