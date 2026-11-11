from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Integer, MetaData, String, text
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
