"""memory outbox and thread ingest watermark

Revision ID: a1b2c3d4e5f6
Revises: d2ce8c68113f
Create Date: 2026-11-10 15:35:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d2ce8c68113f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_type = postgresql.ENUM(
        "thread_closed",
        "idle_checkpoint",
        "user_batch",
        name="memoryoutboxjobtype",
        schema="agent",
    )
    job_type.create(op.get_bind(), checkfirst=True)

    outbox_status = postgresql.ENUM(
        "pending",
        "processing",
        "processed",
        "failed",
        "deferred",
        name="memoryoutboxstatus",
        schema="agent",
    )
    outbox_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "thread",
        sa.Column("ingested_through_conversation_id", sa.Uuid(), nullable=True),
        schema="agent",
    )

    op.create_table(
        "memory_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "job_type",
            postgresql.ENUM(
                "thread_closed",
                "idle_checkpoint",
                "user_batch",
                name="memoryoutboxjobtype",
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
                name="memoryoutboxstatus",
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
        "ix_memory_outbox_status_priority",
        "memory_outbox",
        ["status", "priority", "created_at"],
        schema="agent",
    )
    op.create_index(
        "uniq_memory_outbox_idempotency_active",
        "memory_outbox",
        ["idempotency_key"],
        unique=True,
        schema="agent",
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.create_index(
        "ix_memory_outbox_user_status",
        "memory_outbox",
        ["user_id", "status"],
        schema="agent",
    )


def downgrade() -> None:
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
    op.drop_column(
        "thread", "ingested_through_conversation_id", schema="agent"
    )
    postgresql.ENUM(name="memoryoutboxstatus", schema="agent").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="memoryoutboxjobtype", schema="agent").drop(
        op.get_bind(), checkfirst=True
    )
