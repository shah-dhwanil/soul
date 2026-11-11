"""Graphiti episode ingestion helpers."""

import logging
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
    enrich_episode_body_with_calendar,
)
from agent.graphiti.client import create_graphiti
from agent.pg.models import Conversation

logger = logging.getLogger(__name__)


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
    body = enrich_episode_body_with_calendar(
        body,
        user_messages=[(c.started_at, c.user_message) for c in conversations],
    )
    ref_time = conversations[-1].finished_at
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=UTC)
    graphiti = await create_graphiti(build_indices=False)
    try:
        # graphiti-core 0.31+ treats add_episode(uuid=...) as load-existing, not create.
        results = await graphiti.add_episode(
            name=f"batch:{idempotency_key[:120]}",
            episode_body=body,
            source_description="Wren user conversation batch",
            reference_time=ref_time,
            source=EpisodeType.message,
            group_id=user_id,
            entity_types=ENTITY_TYPES,
            edge_types=EDGE_TYPES,
            edge_type_map=EDGE_TYPE_MAP,
            custom_extraction_instructions=CUSTOM_EXTRACTION_INSTRUCTIONS,
        )
        episode_uuid = results.episode.uuid
        logger.info(
            "graphiti ingest ok idempotency_key=%s episode_uuid=%s",
            idempotency_key,
            episode_uuid,
        )
    finally:
        await graphiti.close()
    return episode_uuid
