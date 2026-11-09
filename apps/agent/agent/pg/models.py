from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData, text
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

class ThreadStatus(str,Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

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
    status: Mapped[ThreadStatus] = mapped_column(nullable=False, default="active")
    
    __table_args__ = (
        Index(
            "uniq_active_thread",
            "user_id",
            unique=True,  # Makes it a unique index
            postgresql_where=text("status = 'active'"),
        ),
    )

class Conversation(BaseModel):
    __tablename__ = "conversation"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(nullable=False)
    user_message: Mapped[str] = mapped_column(nullable=False)
    agent_response: Mapped[str] = mapped_column(nullable=False)
    final_state: Mapped[dict[str,Any]] = mapped_column(JSONB,nullable=False, default=False)
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