#!/usr/bin/env python3
"""Ingest a single user message through the same Graphiti path as production.

Builds a synthetic Conversation row, then calls add_episode_for_batch (episode body,
reference_time, ENTITY_TYPES, CUSTOM_EXTRACTION_INSTRUCTIONS) exactly as IngestService does.

Examples:
  uv run python scripts/ingest_message_graphiti.py --dry-run
  uv run python scripts/ingest_message_graphiti.py --user-id debug-dhwanil \\
    --said-at 2026-11-11T10:30:00+00:00
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from agent.graphiti import build_episode_body, resolve_next_monday
from agent.graphiti.ingest import add_episode_for_batch, conversations_to_ingest_turns
from agent.graphiti.episode import IngestTurn
from agent.logging_config import configure_logging
from agent.pg.models import Conversation
from agent.services.memory import MemoryService
from agent.config import get_settings

DEFAULT_MESSAGE = (
    "Memory because i have an interview scheduled for next monday at vel labs "
    "which build context aware and hyper realistic chatbots."
)

DEFAULT_ASSISTANT = (
    "That sounds like an exciting opportunity. How are you feeling about the interview?"
)


def _parse_said_at(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prod-parity Graphiti ingest for one message")
    parser.add_argument("--user-id", default="debug-ingest-script")
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--assistant-reply", default=DEFAULT_ASSISTANT)
    parser.add_argument(
        "--said-at",
        default="2026-11-11T10:30:00+00:00",
        help="When the user sent the message (conversation.started_at)",
    )
    parser.add_argument(
        "--turn-seconds",
        type=float,
        default=2.0,
        help="Gap between started_at and finished_at",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print episode body only; do not call Graphiti",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="After ingest, run memory search queries",
    )
    return parser.parse_args()


def _synthetic_conversation(
    *,
    message: str,
    assistant: str,
    said_at: datetime,
    turn_seconds: float,
) -> Conversation:
    finished = said_at + timedelta(seconds=turn_seconds)
    return Conversation(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        user_message=message,
        agent_response=assistant,
        final_state={},
        started_at=said_at,
        finished_at=finished,
    )


async def _main() -> int:
    load_dotenv()
    configure_logging()
    args = _parse_args()
    said_at = _parse_said_at(args.said_at)
    conv = _synthetic_conversation(
        message=args.message,
        assistant=args.assistant_reply,
        said_at=said_at,
        turn_seconds=args.turn_seconds,
    )

    turns = conversations_to_ingest_turns([conv])
    body = build_episode_body(turns)
    expected_monday = resolve_next_monday(said_at)

    print("=== ingest_message_graphiti (prod-parity) ===")
    print(f"user_id:           {args.user_id}")
    print(f"conversation_id:   {conv.id}")
    print(f"started_at:        {conv.started_at.isoformat()}")
    print(f"finished_at:       {conv.finished_at.isoformat()}")
    print(f"reference_time:    {conv.finished_at.isoformat()} (last conv finished_at)")
    print(f"expected_next_monday (anchor=said_at): {expected_monday.isoformat()}")
    print("--- episode_body ---")
    print(body)
    print("--- end episode_body ---")

    if args.dry_run:
        print("(dry-run: skipping Graphiti add_episode)")
        return 0

    idempotency_key = f"script:{args.user_id}:{said_at.isoformat()}"
    episode_uuid = await add_episode_for_batch(
        user_id=args.user_id,
        idempotency_key=idempotency_key,
        conversations=[conv],
    )
    print(f"episode_uuid: {episode_uuid}")

    if args.search:
        settings = get_settings()
        mem = MemoryService(settings)
        queries = [
            "interview vel labs next monday",
            "interview scheduled",
        ]
        facts, degraded = await mem.search(args.user_id, queries)
        print(f"memory_degraded: {degraded}")
        for item in facts:
            print(f"  [{item['query']}] {item['fact']}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(_main()))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
