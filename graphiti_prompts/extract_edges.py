"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel, Field

from .models import ChatPrompt, Message, PromptFunction, PromptVersion
from .prompt_helpers import to_prompt_json


class Edge(BaseModel):
    source_entity_name: str = Field(
        ..., description='The name of the source entity from the ENTITIES list'
    )
    target_entity_name: str = Field(
        ..., description='The name of the target entity from the ENTITIES list'
    )
    relation_type: str = Field(
        ...,
        description='The type of relationship between the entities, in SCREAMING_SNAKE_CASE (e.g., WORKS_AT, LIVES_IN, IS_FRIENDS_WITH)',
    )
    fact: str = Field(
        ...,
        description='A natural language description of the relationship between the entities, paraphrased from the source text',
    )
    valid_at: str | None = Field(
        None,
        description='The date and time when the relationship or assertion described by the edge fact became true or was established. Future-tense plans/promises use the statement reference time, not the future occurrence date. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS.SSSSSSZ)',
    )
    invalid_at: str | None = Field(
        None,
        description='The date and time when the relationship described by the edge fact stopped being true or ended. Soft deadlines are not invalid_at values. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS.SSSSSSZ)',
    )
    episode_indices: list[int] = Field(
        default_factory=lambda: [0],
        description='List of episode numbers (0-indexed) that this fact was derived from. '
        'When processing a single episode, this should be [0].',
    )


class ExtractedEdges(BaseModel):
    edges: list[Edge]


class EdgeTimestamps(BaseModel):
    """Temporal bounds extracted from a fact."""

    valid_at: str | None = Field(
        None,
        description='When the fact became true. Future-tense plans/promises use the reference time, not the future occurrence date. ISO 8601 with Z suffix (e.g., 2025-04-30T00:00:00Z)',
    )
    invalid_at: str | None = Field(
        None,
        description='When the fact stopped being true. Soft deadlines are not invalid_at values. ISO 8601 with Z suffix (e.g., 2025-04-30T00:00:00Z)',
    )


class BatchEdgeTimestamps(BaseModel):
    """Temporal bounds for a batch of facts."""

    timestamps: list[EdgeTimestamps] = Field(
        ..., description='Timestamps for each fact, in the same order as the input facts'
    )


class Prompt(Protocol):
    edge: PromptVersion
    extract_attributes: PromptVersion
    extract_timestamps: PromptVersion
    extract_timestamps_batch: PromptVersion


class Versions(TypedDict):
    edge: PromptFunction
    extract_attributes: PromptFunction
    extract_timestamps: PromptFunction
    extract_timestamps_batch: PromptFunction


_TIME_RULES = """- Resolve relative expressions ("last week", "yesterday") from the reference time.
- Ongoing (present-tense) fact: valid_at = reference time.
- Future plan, promise, scheduled event, or deadline: valid_at = reference time, NOT the future date. Keep the future date in the fact text. A soft deadline ("by March 2026") is never invalid_at.
- Use a future invalid_at only for an ongoing state that ends then ("unavailable until December 25, 2024").
- If a change or end is expressed, set invalid_at to that time.
- Leave both null if no time is stated or resolvable. NEVER infer dates from unrelated events.
- Date only: assume 00:00:00. Year only: January 1st 00:00:00. Format: ISO 8601 with Z suffix (2025-04-30T00:00:00Z).
- Example (reference 2020-01-01T00:00:00Z): "Emma will relocate to Tokyo on December 25, 2022" -> valid_at 2020-01-01T00:00:00Z, invalid_at null."""


def edge(context: dict[str, Any]) -> list[Message]:
    edge_types_section = ''
    if context.get('edge_types'):
        relation_type_rules = (
            '- Use one of the provided fact_type_name values as the relation_type.\n'
            '- If a relationship does not match any FACT_TYPE, skip it. Do not derive a new '
            'relation_type.'
            if context.get('strict_edge_types', False)
            else '- If the relationship matches a FACT_TYPE (considering the entity type signature), '
            'use that fact_type_name as the `relation_type`.\n'
            '- Otherwise, derive a `relation_type` in SCREAMING_SNAKE_CASE '
            '(e.g., WORKS_AT, LIVES_IN, IS_FRIENDS_WITH).'
        )
        edge_types_section = f"""
<FACT_TYPES>
{to_prompt_json(context['edge_types'])}
</FACT_TYPES>

# RELATION TYPE RULES

{relation_type_rules}
"""

    return [
        Message(
            role='system',
            content='You are an expert fact extractor that extracts fact triples from text, with '
            'relevant date information. The CURRENT_MESSAGE may contain multiple episodes, each '
            "with its own timestamp; use each episode's timestamp to resolve temporal references "
            'within that episode. REFERENCE_TIME is the fallback when no per-episode timestamp exists.',
        ),
        Message(
            role='user',
            content=f"""
<PREVIOUS_MESSAGES>
{to_prompt_json(context['previous_episodes'])}
</PREVIOUS_MESSAGES>

<CURRENT_MESSAGE>
{context['episode_content']}
</CURRENT_MESSAGE>

<ENTITIES>
{to_prompt_json(context['nodes'])}
</ENTITIES>

<REFERENCE_TIME>
{context['reference_time']}  # ISO 8601 (UTC); used to resolve relative time mentions
</REFERENCE_TIME>
{edge_types_section}
# TASK
Extract factual relationships between the given ENTITIES from the CURRENT MESSAGE: facts clearly stated or unambiguously implied, usable as knowledge-graph edges. Use names rather than pronouns. Use PREVIOUS_MESSAGES only to disambiguate references.

{context['custom_extraction_instructions']}

# RULES

1. `source_entity_name` and `target_entity_name` must be exact `name` values from ENTITIES (other names cause the edge to be rejected) and must be two DISTINCT entities.
2. Do not drop a concrete detail about a single entity (brand, item, quantity, place, named activity). Anchor it to a second entity in ENTITIES to form a triple (e.g. Nate -> PLAYS_GAMES_ON -> Gamecube). Skip only when no second entity fits, or the statement is a vague state with no detail ("Alice feels happy").
3. Do not emit redundant facts, even across episodes. A later episode that adds specifics (brand, count, color, location) to an earlier fact is a NEW fact. If two episodes convey the same specificity, emit once and list both in `episode_indices`.
4. The `fact` must keep every specific detail (proper nouns, brands, models, quantities, colors, materials, named places/activities). Paraphrase the structure but NEVER generalize ("Gamecube" -> "gaming console", "three screenplays" -> "several screenplays").
5. For multiple episodes, prefer the timestamp of the episode the fact comes from; otherwise use REFERENCE_TIME.

# DATETIME RULES

{_TIME_RULES}
""",
        ),
    ]


def extract_attributes(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content=(
                'You are a fact attribute extraction specialist. '
                'You ONLY emit attribute values explicitly stated in the FACT or already present '
                'in EXISTING ATTRIBUTES. Output strictly the JSON specified by the response '
                'schema — no reasoning, explanation, or commentary in any field.'
            ),
        ),
        Message(
            role='user',
            content=f"""\
Given the FACT, its REFERENCE TIME, and any EXISTING ATTRIBUTES, update the attributes.

HARD RULES:
1. Each value must be (a) a clean value copied or directly normalized from the FACT, (b) the existing value, unchanged, or (c) null.
2. NEVER put reasoning, parenthetical explanations, hedging, alternatives, or explanations of why a value is null into any field. If unknown, use null.
3. A schema description gives the FORMAT of a value; NEVER copy it as the value.
4. "null", "N/A", "unknown", "none", "not specified", or any sentence describing absence is NOT a valid value. Use null.
5. Each value must be a short, well-formed instance of the field's type; otherwise null.
6. Use REFERENCE TIME to resolve relative temporal expressions.
7. Keep existing values unless the FACT explicitly gives a new one.

<FACT>
{context['fact']}
</FACT>

<REFERENCE TIME>
{context['reference_time']}
</REFERENCE TIME>

<EXISTING ATTRIBUTES>
{to_prompt_json(context['existing_attributes'])}
</EXISTING ATTRIBUTES>
""",
        ),
    ]


def extract_timestamps(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You extract temporal bounds from facts. NEVER hallucinate dates.',
        ),
        Message(
            role='user',
            content=f"""Given a FACT and its REFERENCE TIME, determine when the fact became true (valid_at) and when it stopped being true (invalid_at).

Rules:
{_TIME_RULES}

<FACT>
{context['fact']}
</FACT>

<REFERENCE TIME>
{context['reference_time']}
</REFERENCE TIME>
""",
        ),
    ]


def extract_timestamps_batch(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You extract temporal bounds from facts. NEVER hallucinate dates.',
        ),
        Message(
            role='user',
            content=f"""Given a list of FACTS with their REFERENCE TIMES, determine when each fact became true (valid_at) and when it stopped being true (invalid_at). Use each fact's own reference time.

Rules:
{_TIME_RULES}

Return one timestamps entry per fact, in the same order.

<FACTS>
{to_prompt_json(context['facts'])}
</FACTS>
""",
        ),
    ]


versions: Versions = {
    'edge': edge,
    'extract_attributes': extract_attributes,
    'extract_timestamps': extract_timestamps,
    'extract_timestamps_batch': extract_timestamps_batch,
}


class ExtractEdgesPrompts(ABC):
    @abstractmethod
    def edge(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_attributes(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_timestamps(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_timestamps_batch(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultExtractEdgesPrompts(ExtractEdgesPrompts):
    def edge(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(edge(context))

    def extract_attributes(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_attributes(context))

    def extract_timestamps(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_timestamps(context))

    def extract_timestamps_batch(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_timestamps_batch(context))
