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


class EdgeDuplicate(BaseModel):
    duplicate_facts: list[int] = Field(
        ...,
        description='List of idx values of duplicate facts (only from EXISTING FACTS range). Empty list if none.',
    )
    contradicted_facts: list[int] = Field(
        ...,
        description='List of idx values of contradicted facts (from full idx range). Empty list if none.',
    )


class Prompt(Protocol):
    resolve_edge: PromptVersion


class Versions(TypedDict):
    resolve_edge: PromptFunction


def resolve_edge(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a fact deduplication assistant. '
            'NEVER mark facts as contradicted unless the new fact explicitly makes the old fact false.',
        ),
        Message(
            role='user',
            content=f"""
<EXISTING FACTS>
{context['existing_edges']}
</EXISTING FACTS>

<FACT INVALIDATION CANDIDATES>
{context['edge_invalidation_candidates']}
</FACT INVALIDATION CANDIDATES>

<NEW FACT>
{context['new_edge']}
</NEW FACT>

The two lists share CONTINUOUS idx numbering: EXISTING FACTS first, then FACT INVALIDATION CANDIDATES.

1. duplicate_facts: idx values from EXISTING FACTS ONLY (never from INVALIDATION CANDIDATES) whose information is identical to the NEW FACT. NEVER mark as duplicates facts that differ in numeric values, dates, or key qualifiers. Empty list if none.

2. contradicted_facts: idx values from EITHER list that the NEW FACT directly contradicts, i.e. both cannot be true. Requires explicit evidence that the old fact stopped being true or was replaced (termination, replacement, transfer, mutually exclusive current state). Empty list if none.
   - Do NOT infer contradiction from recency, episode/meeting dates, snapshots, section headings ("updates", "status changes"), or a new event involving the same entities.
   - Do NOT contradict a role/ownership/responsibility/membership fact because the NEW FACT describes work, updates, documents, progress, blockers, or collaboration on the same project. Working on a project is compatible with owning or leading it.
   - An existing fact can be both duplicate and contradicted only when the same assertion is restated with an explicit incompatible change.

<EXAMPLE>
idx=0 "Alice joined Acme Corp in 2020" vs NEW "Alice joined Acme Corp in 2020" -> duplicate_facts=[0], contradicted_facts=[]
idx=1 "Alice works at Acme Corp as a software engineer" vs NEW "...as a senior engineer" -> duplicate_facts=[], contradicted_facts=[1] (updated title)
idx=2 "Bob ran 5 miles on Tuesday" vs NEW "Bob ran 3 miles on Wednesday" -> both empty (different events)
</EXAMPLE>
""",
        ),
    ]


versions: Versions = {'resolve_edge': resolve_edge}


class DedupeEdgesPrompts(ABC):
    @abstractmethod
    def resolve_edge(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultDedupeEdgesPrompts(DedupeEdgesPrompts):
    def resolve_edge(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(resolve_edge(context))
