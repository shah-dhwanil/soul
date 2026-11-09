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

from graphiti_core.utils.text_utils import MAX_SUMMARY_CHARS

from .models import ChatPrompt, Message, PromptFunction, PromptVersion
from .prompt_helpers import to_prompt_json
from .snippets import summary_instructions


class ExtractedEntity(BaseModel):
    name: str = Field(..., description='Name of the extracted entity')
    entity_type_id: int = Field(
        description='ID of the classified entity type. '
        'Must be one of the provided entity_type_id integers.',
    )
    episode_indices: list[int] = Field(
        default_factory=lambda: [0],
        description='List of episode numbers (0-indexed) this entity was extracted from. '
        'When processing a single episode, this should be [0].',
    )


class ExtractedEntities(BaseModel):
    extracted_entities: list[ExtractedEntity] = Field(..., description='List of extracted entities')


class EntitySummary(BaseModel):
    summary: str = Field(..., description='Summary of the entity')


class SummarizedEntity(BaseModel):
    name: str = Field(..., description='Name of the entity being summarized')
    summary: str = Field(..., description='Updated summary for the entity')


class SummarizedEntities(BaseModel):
    summaries: list[SummarizedEntity] = Field(
        ...,
        description='List of entity summaries. Only include entities that need summary updates.',
    )


class Prompt(Protocol):
    extract_message: PromptVersion
    extract_json: PromptVersion
    extract_text: PromptVersion
    classify_nodes: PromptVersion
    extract_attributes: PromptVersion
    extract_summary: PromptVersion
    extract_summaries_batch: PromptVersion
    extract_entity_summaries_from_episodes: PromptVersion


class Versions(TypedDict):
    extract_message: PromptFunction
    extract_json: PromptFunction
    extract_text: PromptFunction
    classify_nodes: PromptFunction
    extract_attributes: PromptFunction
    extract_summary: PromptFunction
    extract_summaries_batch: PromptFunction
    extract_entity_summaries_from_episodes: PromptFunction


_NEVER_EXTRACT = """NEVER extract:
- Pronouns, abstract concepts or feelings (joy, growth, motivation), sentence fragments, adjectives, or dates/times.
- Generic nouns: day, life, people, stuff, food, supplies, gear; media (photo, pic, video, post); events/activities (event, game, meeting, class); broad institutions (government, school, company, team, office).
- Bare kinship/relational or animal words (dad, friend, boss, dog, pet). Qualify with the possessor: "Nisha's dad", "Jordan's dog".
- Bare objects or ambiguous nouns that depend on context. Qualify with brand, color, material, or owner ("wool coat", "dog leash"), or skip.

Only extract entities specific enough to be uniquely identifiable when read alone later. Use the most specific form ("road cycling" not "cycling"). When in doubt, do NOT extract."""


def extract_message(context: dict[str, Any]) -> list[Message]:
    sys_prompt = (
        'You are an entity extraction specialist for conversational messages. '
        'NEVER extract abstract concepts, feelings, or generic words.'
    )

    user_prompt = f"""
{_NEVER_EXTRACT}
- The same entity twice (e.g. as speaker label and in body text).

Extract entity nodes explicitly mentioned in the CURRENT MESSAGE. Resolve pronouns (he/she/they/this/that) to the entity they refer to.

<ENTITY TYPES>
{context['entity_types']}
</ENTITY TYPES>

<PREVIOUS MESSAGES>
{to_prompt_json([ep for ep in context['previous_episodes']])}
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
{context['episode_content']}
</CURRENT MESSAGE>

Rules:
1. Always extract the speaker (text before the colon) as the first entity; mentions of the speaker in the body are the same entity.
2. Extract only named or concrete entities from the CURRENT MESSAGE. PREVIOUS MESSAGES are context only.
3. Classify each entity with the matching `entity_type_id` from ENTITY TYPES.
4. Do NOT extract relationships, actions, dates, or times.
5. Name entities explicitly and unambiguously (full names when available).

<EXAMPLE>
Message: "Nisha: My dad is visiting next week. He loves walking his dogs in Riverside Park."
Extract: "Nisha" (speaker), "Nisha's dad" (Person), "Riverside Park" (Location)
Skip: "dad" (bare kinship), "dogs" (bare animal word), "next week" (temporal)
</EXAMPLE>

<EXAMPLE>
Message: "Mary: I forgot Trigger's leash so I couldn't walk him. After that I went road cycling in my new wool coat."
Extract: "Mary" (speaker), "Trigger", "dog leash", "road cycling", "wool coat"
Skip: "leash", "cycling", "coat" (too generic), "dog walk" (activity)
</EXAMPLE>

<EXAMPLE>
Message: "Alex: I shared a pic from the game after the event."
Extract: "Alex" (speaker)
Skip: "pic", "game", "event" (generic nouns)
</EXAMPLE>

{context['custom_extraction_instructions']}
"""
    return [
        Message(role='system', content=sys_prompt),
        Message(role='user', content=user_prompt),
    ]


def extract_json(context: dict[str, Any]) -> list[Message]:
    sys_prompt = (
        'You are an entity extraction specialist for JSON data. '
        'NEVER extract abstract concepts, dates, or generic field values.'
    )

    user_prompt = f"""
{_NEVER_EXTRACT}
- Dates/timestamps, generic field values ("true", "active", "pending"), or meaningless numeric IDs/codes.

Extract entities from the JSON and classify each using ENTITY TYPES.

<ENTITY TYPES>
{context['entity_types']}
</ENTITY TYPES>

<SOURCE DESCRIPTION>
{context['source_description']}
</SOURCE DESCRIPTION>

<JSON>
{context['episode_content']}
</JSON>

Rules:
1. Extract the primary entity the JSON represents (e.g. a "name" or "user" field), plus named entities in other properties.
2. Use full names and the most specific form present in the data.

{context['custom_extraction_instructions']}

<EXAMPLE>
JSON: {{"user": "Jordan Lee", "company": "Acme Corp", "role": "engineer", "start_date": "2024-01-15", "location": "Denver", "active": true}}
Extract: "Jordan Lee" (Person), "Acme Corp" (Organization), "Denver" (Location)
Skip: "engineer" (role), "2024-01-15" (date), "true" (field value)
</EXAMPLE>
"""
    return [
        Message(role='system', content=sys_prompt),
        Message(role='user', content=user_prompt),
    ]


def extract_text(context: dict[str, Any]) -> list[Message]:
    sys_prompt = (
        'You are an entity extraction specialist for unstructured text. '
        'NEVER extract abstract concepts, feelings, or generic words.'
    )

    user_prompt = f"""
{_NEVER_EXTRACT}

Extract entities explicitly mentioned in the TEXT and classify each using ENTITY TYPES.

<ENTITY TYPES>
{context['entity_types']}
</ENTITY TYPES>

<TEXT>
{context['episode_content']}
</TEXT>

Rules:
1. Extract named, concrete entities only. No relationships, actions, or dates/times.
2. Use full names, avoid abbreviations, and qualify bare relatives/associates with the possessor ("Dr. Osei's colleague").

{context['custom_extraction_instructions']}

<EXAMPLE>
Text: "Dr. Amara Osei presented her migraine study results at the AAN conference. The study tracked 340 patients using a new CGRP combination protocol."
Extract: "Dr. Amara Osei" (Person), "AAN" (Organization), "migraine study" (Topic), "CGRP combination protocol" (Object)
Skip: "results", "patients", "conference" (generic), "340" (number)
</EXAMPLE>
"""
    return [
        Message(role='system', content=sys_prompt),
        Message(role='user', content=user_prompt),
    ]


def classify_nodes(context: dict[str, Any]) -> list[Message]:
    sys_prompt = (
        'You are an entity classification specialist. '
        'NEVER assign types not listed in ENTITY TYPES.'
    )

    user_prompt = f"""
<PREVIOUS MESSAGES>
{to_prompt_json([ep for ep in context['previous_episodes']])}
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
{context['episode_content']}
</CURRENT MESSAGE>

<EXTRACTED ENTITIES>
{context['extracted_entities']}
</EXTRACTED ENTITIES>

<ENTITY TYPES>
{context['entity_types']}
</ENTITY TYPES>

Classify each extracted entity with exactly one type from ENTITY TYPES. If none fits, set the type to None.
"""
    return [
        Message(role='system', content=sys_prompt),
        Message(role='user', content=user_prompt),
    ]


def extract_attributes(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content=(
                'You are an entity attribute extraction specialist. '
                'You ONLY emit attribute values explicitly stated in MESSAGES or already present '
                'on the ENTITY. Output strictly the JSON specified by the response schema — '
                'no reasoning, explanation, or commentary in any field.'
            ),
        ),
        Message(
            role='user',
            content=f"""\
Given the MESSAGES and the ENTITY, update its attributes.

HARD RULES:
1. Each value must be (a) a clean value copied or directly normalized from MESSAGES, (b) the existing value on the ENTITY, unchanged, or (c) null.
2. NEVER put reasoning, parenthetical explanations, hedging, alternatives, or explanations of why a value is null into any field. If unknown, use null.
3. A schema description gives the FORMAT of a value; NEVER copy it as the value.
4. "null", "N/A", "unknown", "none", "not specified", or any sentence describing absence is NOT a valid value. Use null.
5. Each value must be a short, well-formed instance of the field's type (phone, URL, industry, address); otherwise null.
6. NEVER infer values from the entity's name, related entities, world knowledge, or prior summaries. Exception: name-part fields (first_name, last_name, ...) may be taken from a full person name present in MESSAGES.
7. If MESSAGES say nothing about an attribute, keep the existing value (or null).

Example:
ENTITY: {{"name": "Northwind", "industry": null}}; MESSAGES mention Northwind only as a posting platform.
GOOD: "industry": null
BAD: "industry": "Content platform (implied by usage context...)"

<MESSAGES>
{to_prompt_json(context['previous_episodes'])}
{to_prompt_json(context['episode_content'])}
</MESSAGES>

<ENTITY>
{context['node']}
</ENTITY>
""",
        ),
    ]


def extract_summary(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that extracts entity summaries from the provided text.',
        ),
        Message(
            role='user',
            content=f"""
Given the MESSAGES and the ENTITY, update the summary combining relevant information from the messages and the existing summary. Under {MAX_SUMMARY_CHARS} characters.

{summary_instructions}

<MESSAGES>
{to_prompt_json(context['previous_episodes'])}
{to_prompt_json(context['episode_content'])}
</MESSAGES>

<ENTITY>
{context['node']}
</ENTITY>
""",
        ),
    ]


def _entity_type_descriptions_section(context: dict[str, Any]) -> str:
    """Build an optional prompt section with entity type descriptions."""
    descriptions = context.get('entity_type_descriptions')
    if not descriptions:
        return ''
    return f"""
<ENTITY_TYPE_DESCRIPTIONS>
{to_prompt_json(descriptions)}
</ENTITY_TYPE_DESCRIPTIONS>
Use these descriptions to decide which facts matter for each entity type. NEVER mention the type or classification in the summary.
"""


def extract_summaries_batch(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that generates concise entity summaries from provided context.',
        ),
        Message(
            role='user',
            content=f"""
Given the MESSAGES and ENTITIES, generate an updated summary for each entity that needs one, under {MAX_SUMMARY_CHARS} characters each.

{summary_instructions}

<MESSAGES>
{to_prompt_json(context['previous_episodes'])}
{to_prompt_json(context['episode_content'])}
</MESSAGES>
{_entity_type_descriptions_section(context)}
<ENTITIES>
{to_prompt_json(context['entities'])}
</ENTITIES>

Combine relevant MESSAGES information with any existing summary. Skip entities with no relevant information and no existing summary.
""",
        ),
    ]


# NOTE: This prompt is semantically mirrored in the Go async summary worker at
# src/lib/graphsummary/processor.go (entitySummarySystemPrompt). Keep both in sync.
_entity_episode_summary_system_prompt = """You maintain dense, factual entity memories from episode text.

Use ONLY facts explicitly stated in EPISODES and durable facts already in EXISTING_SUMMARY. NEVER infer beyond them.

Capture: stable facts; named people, organizations, places, events, and objects linked to the entity; explicit actions, roles, relationships, outcomes; counts; dates and ordering at the highest fidelity available. Prefer newer explicit facts over superseded ones. Keep every supported concrete detail.

Rules:
- NEVER infer preferences, habits, recurrence, causality, or intent from a name or single mention. Call something recurring/preferred only if multiple episodes or one explicit statement support it.
- State the content of what was said directly. Use communication verbs only when the act itself is the fact; avoid "mentioned", "described", "stated", "noted", "discussed", "referenced", "indicated", "reported".
- NEVER mention the source, episodes, messages, summaries, memory, graphs, nodes, types, or categorization. NEVER use "the entity", "suggests", "appears to".
- Use the entity's name or a natural pronoun. NEVER start with "A ", "An ", "This is", or "The " (unless part of the name); lead with the name or a concrete fact.
- If new episodes add no durable fact, return the existing summary unchanged.
- Write 2-6 dense third-person sentences. Return only the summary text.

Example:
Input: {"name": "Jordan Lee", "existing_summary": "Jordan Lee works at Belmont Arts Center.", "episodes": [{"content": "Mina: Jordan Lee presented a ceramics workshop at Belmont Arts Center on March 3, 2025 with 24 attendees on wheel-thrown bowls.\\nOwen: Jordan announced a second April workshop."}]}
GOOD: "Jordan Lee works at Belmont Arts Center. Jordan presented a ceramics workshop there on March 3, 2025 for 24 attendees on wheel-thrown bowls and announced a second April workshop."
BAD: "Jordan Lee seems interested in ceramics. Jordan mentioned teaching and was described as busy.\""""


def extract_entity_summaries_from_episodes(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content=_entity_episode_summary_system_prompt,
        ),
        Message(
            role='user',
            content=f"""Use ONLY facts from the EPISODES. No meta-language about summarization.
Each summary: under {MAX_SUMMARY_CHARS} characters, 2-6 dense third-person sentences, preserving supported names, roles, dates, counts, and changes over time.

For each entity below, write an updated summary from the EPISODES and any existing summary on the entity.

<EPISODES>
{to_prompt_json(context['previous_episodes'])}
{to_prompt_json(context['episode_content'])}
</EPISODES>
{_entity_type_descriptions_section(context)}
<ENTITIES>
{to_prompt_json(context['entities'])}
</ENTITIES>

Skip entities with no relevant information and no existing summary.
""",
        ),
    ]


versions: Versions = {
    'extract_message': extract_message,
    'extract_json': extract_json,
    'extract_text': extract_text,
    'extract_summary': extract_summary,
    'extract_summaries_batch': extract_summaries_batch,
    'extract_entity_summaries_from_episodes': extract_entity_summaries_from_episodes,
    'classify_nodes': classify_nodes,
    'extract_attributes': extract_attributes,
}


class ExtractNodesPrompts(ABC):
    @abstractmethod
    def extract_message(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_json(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_text(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def classify_nodes(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_attributes(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_summary(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_summaries_batch(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def extract_entity_summaries_from_episodes(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultExtractNodesPrompts(ExtractNodesPrompts):
    def extract_message(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_message(context))

    def extract_json(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_json(context))

    def extract_text(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_text(context))

    def classify_nodes(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(classify_nodes(context))

    def extract_attributes(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_attributes(context))

    def extract_summary(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_summary(context))

    def extract_summaries_batch(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_summaries_batch(context))

    def extract_entity_summaries_from_episodes(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(extract_entity_summaries_from_episodes(context))
