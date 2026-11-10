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


class CombinedEntity(BaseModel):
    """Entity extracted by the combined node+edge extraction prompt."""

    name: str = Field(..., description='Name of the extracted entity')
    entity_type_id: int = Field(
        description='ID of the classified entity type. '
        'Must be one of the provided entity_type_id integers.',
    )


class CombinedFact(BaseModel):
    """Relationship fact extracted by the combined node+edge extraction prompt."""

    source_entity_name: str = Field(
        ...,
        description=(
            'The name of the source entity. MUST exactly match an entity `name` in '
            'extracted_entities (including value-like endpoints such as versions).'
        ),
    )
    target_entity_name: str = Field(
        ...,
        description=(
            'The name of the target entity. MUST exactly match an entity `name` in '
            'extracted_entities (including value-like endpoints such as versions).'
        ),
    )
    relation_type: str = Field(
        ...,
        description='The type of relationship between the entities, in SCREAMING_SNAKE_CASE '
        '(e.g., WORKS_AT, LIVES_IN, IS_FRIENDS_WITH)',
    )
    fact: str = Field(
        ...,
        description='A self-contained natural language description of the relationship, '
        'paraphrased from the source text with all specific details preserved',
    )
    episode_indices: list[int] = Field(
        default_factory=lambda: [0],
        description='List of episode numbers (0-indexed) that this fact was derived from. '
        'When processing a single episode, this should be [0].',
    )


class CombinedExtraction(BaseModel):
    """Combined node and edge extraction response."""

    extracted_entities: list[CombinedEntity] = Field(..., description='List of extracted entities')
    edges: list[CombinedFact] = Field(..., description='List of extracted relationship facts')


class Prompt(Protocol):
    extract_message: PromptVersion


class Versions(TypedDict):
    extract_message: PromptFunction


def _build_edge_types_section(
    edge_types: list[dict] | None, strict_edge_types: bool = False
) -> str:
    """Build the optional FACT TYPES section for the combined prompt."""
    if not edge_types:
        return ''
    relation_type_rules = (
        '- Use one of the provided fact_type_name values as the relation_type.\n'
        '- If a relationship does not match any FACT TYPE, skip it. Do not derive a new '
        'relation_type.'
        if strict_edge_types
        else '- When a relationship matches a FACT TYPE, use that fact_type_name as the '
        'relation_type.\n'
        '- If no FACT TYPE fits, derive a relation_type in SCREAMING_SNAKE_CASE\n'
        '  (e.g., WORKS_AT, LIVES_IN, IS_FRIENDS_WITH).'
    )
    return f"""
<FACT TYPES>
{to_prompt_json(edge_types)}
</FACT TYPES>
RELATION TYPE RULES:
{relation_type_rules}
"""


def _build_custom_instructions_section(custom_extraction_instructions: str | None) -> str:
    """Build the optional CUSTOM INSTRUCTIONS section for the combined prompt."""
    if not custom_extraction_instructions:
        return ''
    return f"""
<CUSTOM INSTRUCTIONS>
{custom_extraction_instructions}
</CUSTOM INSTRUCTIONS>
CUSTOM INSTRUCTION RULES:
- CUSTOM INSTRUCTIONS come from the owner of this graph. Apply them. When a CUSTOM INSTRUCTION conflicts with a rule above, the CUSTOM INSTRUCTION wins.
"""


_SYSTEM_PROMPT = 'You build the long-term memory of an AI agent. From each conversation you extract the entities and relationship facts the agent will need later. The original conversation will not be available later, so each fact must stand alone.'


_C2_INSTRUCTION_TEXT = """# Goal
Turn CURRENT MESSAGES into a knowledge graph: entities and facts (edges) between them, so an agent can answer "who said, did, wants, owns, plans, feels, recommends, or knows what" without the source text.

# Good output
- Complete: cover every episode and speaker with real content, including later ones in a long input (preferences, opinions, plans, commitments, requests, emotions, experiences, advice, results). Skip only content-free turns ("Hi!", "Thanks!").
- Attributed: when a named person, account, or organization states, recommends, or does something, that actor is the source entity and the fact names the actor.
- Self-contained: one plain sentence per fact, entity names instead of pronouns, specific details kept (numbers, dates, prices, versions, names).
- Compact: one fact per statement. Keep a list of items from one statement in one fact unless each has its own details; no fact or entity per list item. If the same fact appears in several episodes, emit it once with all episode indices.

# Entities
- Speakers: use the most complete name available; with profile fields (first_name/last_name, given_name/family_name, user_alias, screen_name) use the full personal name. Use "User" only if no name exists.
- Others: named people, organizations, places, products, files, tickets, projects, events, documents, named or described objects, and hobbies/activities someone does ("road cycling"). Use the most specific noun phrase, max 5 words. Use possessive names for a person's possession, pet, project, or creation ("Calvin's guitar"), not the bare noun.
- Do NOT make entities from: pronouns or unresolved references; vague abstractions ("growth", "life"); times, dates, quantities, prices, durations, measurements (keep in fact text, unless a value like a version is itself an edge endpoint); answer options or template tokens; imperative tips ("Buy in bulk" -> topic "bulk buying"); slogans or idioms; tutorial example values ("/path/to/source").
- Each entity once, classified with an entity_type_id from ENTITY TYPES. Extract only from CURRENT MESSAGES; use PREVIOUS MESSAGES and [CONTEXT EPISODE] messages only to resolve references.

# Facts
- source_entity_name and target_entity_name must be names from extracted_entities (add value endpoints such as versions as entities).
- Connect the actor directly to the thing ("Calvin -> PERFORMED_IN -> Tokyo"). Do not route through descriptive nouns ("city lights -> LOCATED_IN -> Tokyo") or turn an actor's claim into a fact between two nouns the actor mentioned.
- Use a self-referencing fact (same source and target) only when a statement concerns one entity and no other fits (routine, feeling, health state: "Evan has a knee injury.").
- Resolve what the current message refers to using PREVIOUS MESSAGES and [CONTEXT EPISODE] messages, and write the resolved fact. [CONTEXT EPISODE] messages are turns between numbered episodes, for reading order only: no facts and no episode index from them.
- episode_indices: the 0-based [Episode N] numbers the fact comes from.
- Write entity names and facts in the dominant language of the source episode; keep proper names as written; relation_type is an English SCREAMING_SNAKE_CASE label.
- State what the source says: no reasoning, hedges ("appears to", "suggests"), or commentary.

# Output
Return only the JSON object: {"extracted_entities":[{"name":"...","entity_type_id":0}],"edges":[{"source_entity_name":"...","target_entity_name":"...","relation_type":"...","fact":"...","episode_indices":[0]}]}."""


def _build_extract_user_prompt(context: dict[str, Any]) -> str:
    return f"""{_C2_INSTRUCTION_TEXT}

<ENTITY TYPES>
{context['entity_types']}
</ENTITY TYPES>
{_build_edge_types_section(context.get('edge_types'), context.get('strict_edge_types', False))}
{_build_custom_instructions_section(context.get('custom_extraction_instructions'))}
<PREVIOUS MESSAGES>
{to_prompt_json([ep for ep in context['previous_episodes']])}
</PREVIOUS MESSAGES>

<CURRENT MESSAGES>
{context['episode_content']}
</CURRENT MESSAGES>
"""


def extract_message(context: dict[str, Any]) -> list[Message]:
    return [
        Message(role='system', content=_SYSTEM_PROMPT),
        Message(role='user', content=_build_extract_user_prompt(context)),
    ]


versions: Versions = {
    'extract_message': extract_message,
}


class ExtractNodesAndEdgesPrompts(ABC):
    @abstractmethod
    def extract_message(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultExtractNodesAndEdgesPrompts(ExtractNodesAndEdgesPrompts):
    def extract_message(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_message(context))
