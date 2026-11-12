"""detection job queue

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-12 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detection_job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_detection_job_status_created",
        "detection_job",
        ["status", "created_at"],
        schema="agent",
    )
    op.create_index(
        "uniq_detection_job_conversation_active",
        "detection_job",
        ["conversation_id"],
        unique=True,
        schema="agent",
        postgresql_where=sa.text("status IN ('pending','processing')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uniq_detection_job_conversation_active",
        table_name="detection_job",
        schema="agent",
    )
    op.drop_index(
        "ix_detection_job_status_created", table_name="detection_job", schema="agent"
    )
    op.drop_table("detection_job", schema="agent")
