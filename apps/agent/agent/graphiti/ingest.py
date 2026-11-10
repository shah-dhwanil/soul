"""Graphiti episode ingestion helpers."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from graphiti_core.nodes import EpisodeType

from agent.graphiti import (
    CUSTOM_EXTRACTION_INSTRUCTIONS,
    EDGE_TYPE_MAP,
    EDGE_TYPES,
    ENTITY_TYPES,
    IngestTurn,
    build_episode_body,
)
from agent.graphiti.client import create_graphiti
from agent.pg.models import Conversation


def episode_uuid_for_key(idempotency_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"wren:episode:{idempotency_key}"))


def conversations_to_ingest_turns(
    conversations: list[Conversation],
) -> list[IngestTurn]:
    turns: list[IngestTurn] = []
    for conv in conversations:
        turns.append(
            IngestTurn(
                role="user",
                text=conv.user_message,
                occurred_at=conv.started_at,
            )
        )
        turns.append(
            IngestTurn(
                role="assistant",
                text=conv.agent_response,
                occurred_at=conv.finished_at,
            )
        )
    return turns


async def add_episode_for_batch(
    *,
    user_id: str,
    idempotency_key: str,
    conversations: list[Conversation],
) -> str:
    if not conversations:
        raise ValueError("conversations must not be empty")
    turns = conversations_to_ingest_turns(conversations)
    body = build_episode_body(turns)
    ref_time = conversations[-1].finished_at
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=UTC)
    episode_uuid = episode_uuid_for_key(idempotency_key)
    graphiti = await create_graphiti(build_indices=False)
    try:
        await graphiti.add_episode(
            name=f"batch:{idempotency_key[:120]}",
            episode_body=body,
            source_description="Wren user conversation batch",
            reference_time=ref_time,
            source=EpisodeType.message,
            group_id=user_id,
            uuid=episode_uuid,
            entity_types=ENTITY_TYPES,
            edge_types=EDGE_TYPES,
            edge_type_map=EDGE_TYPE_MAP,
            custom_extraction_instructions=CUSTOM_EXTRACTION_INSTRUCTIONS,
        )
    finally:
        await graphiti.close()
    return episode_uuid
