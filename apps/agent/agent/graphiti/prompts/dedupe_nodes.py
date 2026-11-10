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


class NodeDuplicate(BaseModel):
    id: int = Field(..., description='integer id of the entity')
    name: str = Field(
        ...,
        description='Name of the entity. Should be the most complete and descriptive name of the entity. Do not include any JSON formatting in the Entity name such as {}.',
    )
    duplicate_candidate_id: int = Field(
        ...,
        description='candidate_id of the matching EXISTING ENTITY, or -1 if no duplicate exists.',
    )


class NodeResolutions(BaseModel):
    entity_resolutions: list[NodeDuplicate] = Field(..., description='List of resolved nodes')


class Prompt(Protocol):
    node: PromptVersion
    node_list: PromptVersion
    nodes: PromptVersion


class Versions(TypedDict):
    node: PromptFunction
    node_list: PromptFunction
    nodes: PromptFunction


_SYSTEM = (
    'You are an entity deduplication assistant. '
    'NEVER fabricate entity names or mark distinct entities as duplicates.'
)

_DEDUPE_RULES = """Entities are duplicates only if they refer to the *same real-world object or concept*. A descriptive label that clearly refers to a named entity in context is a duplicate. NEVER mark entities as duplicates if they are related but distinct, or have similar names/purposes but are separate instances or concepts."""

_EXAMPLES = """<EXAMPLE>
"Sam" vs existing [{"candidate_id": 0, "name": "Sam", "entity_types": ["Person"]}] -> 0 (same person)
"NYC" vs existing [{"candidate_id": 0, "name": "New York City"}, {"candidate_id": 1, "name": "New York Knicks"}] -> 0 (abbreviation)
"Java" (language) vs existing [{"candidate_id": 0, "name": "Java", "summary": "An island in Indonesia"}] -> -1 (same name, different things)
"Marco's car" vs existing [{"candidate_id": 0, "name": "Marco's vehicle"}] -> 0 (synonym, same possessor)
</EXAMPLE>"""


def node(context: dict[str, Any]) -> list[Message]:
    return [
        Message(role='system', content=_SYSTEM),
        Message(
            role='user',
            content=f"""
<PREVIOUS MESSAGES>
{to_prompt_json(context['previous_episodes'])}
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
{context['episode_content']}
</CURRENT MESSAGE>

<NEW ENTITY>
{to_prompt_json(context['extracted_node'])}
</NEW ENTITY>

<ENTITY TYPE DESCRIPTION>
{to_prompt_json(context['entity_type_description'])}
</ENTITY TYPE DESCRIPTION>

<EXISTING ENTITIES>
{to_prompt_json(context['existing_nodes'])}
</EXISTING ENTITIES>

{_DEDUPE_RULES}

Task: compare the NEW ENTITY against each EXISTING ENTITY (by `candidate_id`). Return the `candidate_id` of the match as `duplicate_candidate_id`, or -1 if there is no match or you are unsure.

{_EXAMPLES}
""",
        ),
    ]


def nodes(context: dict[str, Any]) -> list[Message]:
    return [
        Message(role='system', content=_SYSTEM),
        Message(
            role='user',
            content=f"""
<PREVIOUS MESSAGES>
{to_prompt_json(context['previous_episodes'])}
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
{context['episode_content']}
</CURRENT MESSAGE>

<ENTITIES>
{to_prompt_json(context['extracted_nodes'])}
</ENTITIES>

<EXISTING ENTITIES>
{to_prompt_json(context['existing_nodes'])}
</EXISTING ENTITIES>

Each ENTITY was extracted from the CURRENT MESSAGE. For each, decide whether it duplicates an EXISTING ENTITY.

{_DEDUPE_RULES}

ENTITIES contains {len(context['extracted_nodes'])} entities with IDs 0 through {len(context['extracted_nodes']) - 1}.
Your response MUST include EXACTLY {len(context['extracted_nodes'])} resolutions with IDs 0 through {len(context['extracted_nodes']) - 1}. Do not skip or add IDs.

For every entity provide:
- `id`: integer id from ENTITIES
- `name`: the best full name (keep the original unless a duplicate has a more complete name)
- `duplicate_candidate_id`: `candidate_id` of the best EXISTING ENTITY match, or -1 if none

{_EXAMPLES}
""",
        ),
    ]


def node_list(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are an entity deduplication assistant that groups duplicate nodes by UUID.',
        ),
        Message(
            role='user',
            content=f"""
<NODES>
{to_prompt_json(context['nodes'])}
</NODES>

Task:
1. Group duplicate nodes into lists of uuids. Each uuid appears EXACTLY once; a node with no duplicates gets a list of one uuid.
2. For each group, write a short summary synthesizing the nodes' summaries.

<EXAMPLE>
Input: [{{"uuid": "a1", "name": "NYC", "summary": "New York City"}}, {{"uuid": "b2", "name": "New York City", "summary": "The city of New York"}}, {{"uuid": "c3", "name": "Los Angeles", "summary": "City in California"}}]
Result: [{{"uuids": ["a1", "b2"], "summary": "New York City, also known as NYC"}}, {{"uuids": ["c3"], "summary": "City in California"}}]
</EXAMPLE>
""",
        ),
    ]


versions: Versions = {'node': node, 'node_list': node_list, 'nodes': nodes}


class DedupeNodesPrompts(ABC):
    @abstractmethod
    def node(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def node_list(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def nodes(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultDedupeNodesPrompts(DedupeNodesPrompts):
    def node(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(node(context))

    def node_list(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(node_list(context))

    def nodes(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(nodes(context))
