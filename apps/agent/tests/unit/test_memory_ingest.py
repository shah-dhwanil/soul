from datetime import UTC, datetime
from uuid import uuid4

from agent.graphiti.ingest import (
    conversations_to_ingest_turns,
    episode_uuid_for_key,
)
from agent.pg.models import Conversation
from agent.services.memory_worker import batch_meets_ingest_threshold


def test_batch_meets_ingest_threshold() -> None:
    assert not batch_meets_ingest_threshold(9, 10)
    assert batch_meets_ingest_threshold(10, 10)
    assert batch_meets_ingest_threshold(15, 10)


def test_episode_uuid_is_deterministic() -> None:
    a = episode_uuid_for_key("user_batch:alice")
    b = episode_uuid_for_key("user_batch:alice")
    c = episode_uuid_for_key("user_batch:bob")
    assert a == b
    assert a != c


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
