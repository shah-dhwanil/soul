from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from agent.graphiti.ingest import (
    add_episode_for_batch,
    conversations_to_ingest_turns,
    episode_uuid_for_key,
)
from agent.config import Settings
from agent.pg.models import Conversation, MemoryOutboxJobType
from agent.services.memory_worker import (
    batch_meets_ingest_threshold,
    ingest_min_count_for_job,
)


def test_batch_meets_ingest_threshold() -> None:
    assert not batch_meets_ingest_threshold(9, 10)
    assert batch_meets_ingest_threshold(10, 10)
    assert batch_meets_ingest_threshold(15, 10)
    assert batch_meets_ingest_threshold(1, 1)
    assert not batch_meets_ingest_threshold(0, 1)


def test_ingest_min_count_for_job() -> None:
    settings = Settings(
        min_conversations_for_ingest=10,
        min_conversations_for_idle_flush=1,
    )
    assert (
        ingest_min_count_for_job(
            settings, MemoryOutboxJobType.USER_BATCH, priority=0
        )
        == 10
    )
    assert (
        ingest_min_count_for_job(
            settings, MemoryOutboxJobType.USER_BATCH, priority=1
        )
        == 1
    )
    assert (
        ingest_min_count_for_job(
            settings, MemoryOutboxJobType.THREAD_CLOSED, priority=1
        )
        == 10
    )


def test_episode_uuid_is_deterministic() -> None:
    a = episode_uuid_for_key("user_batch:alice")
    b = episode_uuid_for_key("user_batch:alice")
    c = episode_uuid_for_key("user_batch:bob")
    assert a == b
    assert a != c


@pytest.mark.asyncio
async def test_add_episode_for_batch_omits_uuid_kwarg() -> None:
    created_uuid = str(uuid4())
    mock_graphiti = MagicMock()
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(episode=SimpleNamespace(uuid=created_uuid))
    )
    mock_graphiti.close = AsyncMock()
    now = datetime.now(UTC)
    conv = Conversation(
        id=uuid4(),
        thread_id=uuid4(),
        user_message="hi",
        agent_response="hey",
        final_state={},
        started_at=now,
        finished_at=now,
    )
    with patch(
        "agent.graphiti.ingest.create_graphiti", AsyncMock(return_value=mock_graphiti)
    ):
        out = await add_episode_for_batch(
            user_id="dh",
            idempotency_key="user_batch:verify",
            conversations=[conv],
        )
    assert out == created_uuid
    assert "uuid" not in mock_graphiti.add_episode.await_args.kwargs


def test_conversations_to_ingest_turns_alternates_roles() -> None:
    now = datetime.now(UTC)
    conv = Conversation(
        id=uuid4(),
        thread_id=uuid4(),
        user_message="hi",
        agent_response="hey",
        final_state={},
        started_at=now,
        finished_at=now,
    )
    turns = conversations_to_ingest_turns([conv])
    assert len(turns) == 2
    assert turns[0].role == "user"
    assert turns[1].role == "assistant"
