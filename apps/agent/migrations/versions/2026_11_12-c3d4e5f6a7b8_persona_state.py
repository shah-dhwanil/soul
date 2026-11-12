"""persona state tables and conversation persona columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-12 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts_columns() -> list[sa.Column]:
    return [
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
    ]


def _jsonb(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )


def _int(name: str, default: int = 0) -> sa.Column:
    return sa.Column(
        name, sa.Integer(), nullable=False, server_default=sa.text(str(default))
    )


def upgrade() -> None:
    op.create_table(
        "user_persona",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("temperament", sa.String(), nullable=False),
        sa.Column("locale", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        _jsonb("dials"),
        _jsonb("learned_dials"),
        _int("stage", 1),
        _int("dependency_level", 0),
        sa.Column("dependency_level_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "dependency_last_level2_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "dependency_low_baseline",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "dependency_explained_until", sa.DateTime(timezone=True), nullable=True
        ),
        _jsonb("settings"),
        _jsonb("counters"),
        sa.Column("stage_frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_attunement_review_at", sa.DateTime(timezone=True), nullable=True
        ),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("user_id"),
        schema="agent",
    )

    op.create_table(
        "user_trait",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default=sa.text("'noticed'")
        ),
        _int("positive_count"),
        _int("negative_count"),
        _int("neutral_count"),
        _int("distinct_days"),
        sa.Column(
            "sensitive", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_landed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
        schema="agent",
    )
    op.create_index(
        "ix_user_trait_user_status",
        "user_trait",
        ["user_id", "status"],
        schema="agent",
    )

    op.create_table(
        "user_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("signal", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "counts_toward_stage",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        _jsonb("metadata"),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
        schema="agent",
    )
    op.create_index(
        "ix_user_signal_user_kind",
        "user_signal",
        ["user_id", "kind"],
        schema="agent",
    )
    op.create_index(
        "ix_user_signal_user_occurred",
        "user_signal",
        ["user_id", "occurred_at"],
        schema="agent",
    )
    op.create_index(
        "ix_user_signal_user_expires",
        "user_signal",
        ["user_id", "expires_at"],
        schema="agent",
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    op.create_table(
        "user_leaning",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default=sa.text("'noticed'")
        ),
        _int("positive_count"),
        _int("negative_count"),
        _int("distinct_days"),
        sa.Column(
            "baseline_engagement",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("tilt_started_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_columns(),
        sa.PrimaryKeyConstraint("id"),
        schema="agent",
    )
    op.create_index(
        "ix_user_leaning_user_status",
        "user_leaning",
        ["user_id", "status"],
        schema="agent",
    )

    op.add_column(
        "conversation", sa.Column("mode", sa.String(), nullable=True), schema="agent"
    )
    op.add_column(
        "conversation",
        sa.Column("concern_tier", sa.String(), nullable=True),
        schema="agent",
    )
    op.add_column(
        "conversation",
        sa.Column("dependency_level", sa.Integer(), nullable=True),
        schema="agent",
    )
    op.add_column(
        "conversation", sa.Column("stage", sa.Integer(), nullable=True), schema="agent"
    )
    op.add_column(
        "conversation",
        sa.Column(
            "asked_question",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="agent",
    )
    op.add_column(
        "conversation",
        sa.Column("trait_used", sa.String(), nullable=True),
        schema="agent",
    )
    op.add_column(
        "conversation",
        sa.Column(
            "validation",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="agent",
    )
    op.add_column(
        "conversation",
        sa.Column("persona_version", sa.String(), nullable=True),
        schema="agent",
    )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for persona state")
