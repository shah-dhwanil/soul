from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    MetaData,
    String,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    metadata = MetaData(schema="agent")


class BaseModel(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class MemoryIngestJobType(str, Enum):
    THREAD_CLOSED = "thread_closed"
    IDLE_CHECKPOINT = "idle_checkpoint"
    USER_BATCH = "user_batch"


class MemoryIngestJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEFERRED = "deferred"


class MemoryIngestionStateStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


class TrustSignal(str, Enum):
    S1 = "s1"
    S2 = "s2"
    S3 = "s3"
    S4 = "s4"
    S5 = "s5"
    S6 = "s6"


class DependencySignal(str, Enum):
    D1 = "d1"
    D2 = "d2"
    D3 = "d3"
    D4 = "d4"
    D5 = "d5"
    D6 = "d6"


class TraitStatus(str, Enum):
    NOTICED = "noticed"
    CANDIDATE = "candidate"
    TRIAL = "trial"
    ACTIVE = "active"
    DORMANT = "dormant"
    RETIRED = "retired"


class LeaningStatus(str, Enum):
    NOTICED = "noticed"
    CANDIDATE = "candidate"
    TILT = "tilt"
    ACTIVE = "active"
    DORMANT = "dormant"
    RETIRED = "retired"


class Thread(BaseModel):
    __tablename__ = "thread"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    status: Mapped[ThreadStatus] = mapped_column(
        SAEnum(
            ThreadStatus,
            name="threadstatus",
            schema="agent",
            values_callable=lambda members: [m.value for m in members],
            native_enum=True,
        ),
        nullable=False,
        default=ThreadStatus.ACTIVE,
    )

    __table_args__ = (
        Index(
            "uniq_active_thread",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class Conversation(BaseModel):
    __tablename__ = "conversation"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(nullable=False)
    user_message: Mapped[str] = mapped_column(nullable=False)
    agent_response: Mapped[str] = mapped_column(nullable=False)
    final_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    mode: Mapped[str | None] = mapped_column(String, nullable=True)
    concern_tier: Mapped[str | None] = mapped_column(String, nullable=True)
    dependency_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asked_question: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    trait_used: Mapped[str | None] = mapped_column(String, nullable=True)
    validation: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    persona_version: Mapped[str | None] = mapped_column(String, nullable=True)


class MemoryOutbox(BaseModel):
    """One durable row per conversation at turn commit (audit / queue reference)."""

    __tablename__ = "memory_outbox"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[str] = mapped_column(nullable=False)
    thread_id: Mapped[UUID] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uniq_memory_outbox_conversation",
            "conversation_id",
            unique=True,
        ),
        Index("ix_memory_outbox_user_created", "user_id", "created_at"),
    )


class MemoryIngestionState(BaseModel):
    __tablename__ = "memory_ingestion_state"

    conversation_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=False)
    thread_id: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[MemoryIngestionStateStatus] = mapped_column(
        SAEnum(
            MemoryIngestionStateStatus,
            name="memoryingestionstatestatus",
            schema="agent",
            values_callable=lambda members: [m.value for m in members],
            native_enum=True,
        ),
        nullable=False,
        default=MemoryIngestionStateStatus.PENDING,
    )
    episode_uuid: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_memory_ingestion_state_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_memory_ingestion_state_thread_status",
            "thread_id",
            "status",
        ),
    )


class MemoryIngestJob(BaseModel):
    __tablename__ = "memory_ingest_job"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(nullable=False)
    job_type: Mapped[MemoryIngestJobType] = mapped_column(
        SAEnum(
            MemoryIngestJobType,
            name="memoryingestjobtype",
            schema="agent",
            values_callable=lambda members: [m.value for m in members],
            native_enum=True,
        ),
        nullable=False,
    )
    thread_id: Mapped[UUID | None] = mapped_column(nullable=True)
    status: Mapped[MemoryIngestJobStatus] = mapped_column(
        SAEnum(
            MemoryIngestJobStatus,
            name="memoryingestjobstatus",
            schema="agent",
            values_callable=lambda members: [m.value for m in members],
            native_enum=True,
        ),
        nullable=False,
        default=MemoryIngestJobStatus.PENDING,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str] = mapped_column(nullable=False)
    conversation_from_id: Mapped[UUID | None] = mapped_column(nullable=True)
    conversation_to_id: Mapped[UUID | None] = mapped_column(nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    episode_uuid: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "uniq_memory_ingest_job_idempotency_active",
            "idempotency_key",
            unique=True,
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        Index(
            "ix_memory_ingest_job_status_priority",
            "status",
            "priority",
            "created_at",
        ),
        Index("ix_memory_ingest_job_user_status", "user_id", "status"),
    )


# Persona state tables. Never log message content from any of these tables.


class UserPersona(BaseModel):
    __tablename__ = "user_persona"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    temperament: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)
    dials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    learned_dials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dependency_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    dependency_level_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dependency_last_level2_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dependency_low_baseline: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    dependency_explained_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    counters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    stage_frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attunement_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserTrait(BaseModel):
    __tablename__ = "user_trait"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=TraitStatus.NOTICED.value
    )
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_landed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_user_trait_user_status", "user_id", "status"),)


class UserSignal(BaseModel):
    __tablename__ = "user_signal"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    signal: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    counts_toward_stage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    # "metadata" is reserved on declarative classes; the DB column keeps the name.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_user_signal_user_kind", "user_id", "kind"),
        Index("ix_user_signal_user_occurred", "user_id", "occurred_at"),
        Index(
            "ix_user_signal_user_expires",
            "user_id",
            "expires_at",
            postgresql_where=text("expires_at IS NOT NULL"),
        ),
    )


class UserLeaning(BaseModel):
    __tablename__ = "user_leaning"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=LeaningStatus.NOTICED.value
    )
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_engagement: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    tilt_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_user_leaning_user_status", "user_id", "status"),)
