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


class SagaSummary(BaseModel):
    summary: str = Field(
        ...,
        description=f'Factual knowledge brief. Under {MAX_SUMMARY_CHARS} characters.',
    )


class Prompt(Protocol):
    summarize_saga: PromptVersion


class Versions(TypedDict):
    summarize_saga: PromptFunction


def summarize_saga(context: dict[str, Any]) -> list[Message]:
    saga_name = context.get('saga_name', 'Unknown')
    existing_summary = context.get('existing_summary', '')
    episodes = context.get('episodes', [])

    episodes_text = '\n---\n'.join(episodes) if episodes else '(no messages)'

    existing_summary_section = ''
    if existing_summary:
        existing_summary_section = f"""
<EXISTING_KNOWLEDGE>
{existing_summary}
</EXISTING_KNOWLEDGE>
Merge new facts from MESSAGES into EXISTING_KNOWLEDGE. Prefer newer facts when they contradict older ones. If MESSAGES add nothing durable, return it unchanged.
"""

    return [
        Message(
            role='system',
            content=(
                'You extract durable knowledge from message threads. '
                'Output a factual knowledge brief — facts, decisions, preferences, plans, '
                'entities, and relationships — that stands alone without reference to the '
                'original messages. '
                f'Stay under {MAX_SUMMARY_CHARS} characters.'
            ),
        ),
        Message(
            role='user',
            content=f"""Extract all durable knowledge from the MESSAGES into a factual brief for the topic "{saga_name}".

NEVER use meta-language ("mentioned", "discussed", "noted", "stated", "described", "talked about", "brought up") or refer to the messages, thread, or participants' communicative acts. NEVER begin with "This conversation", "The thread", or "The discussion". The brief must read as if no conversation happened. State facts directly.
NEVER infer preferences or habits from one passing mention. Capture explicit statements ("I prefer X") as stated preferences attributed to that person.

Capture explicitly stated: facts and details (names, dates, numbers, locations); decisions and outcomes; preferences and requirements; plans, next steps, commitments; relationships (who works where, who owns what); state changes (was X, now Y).

Write 2-6 dense third-person sentences, keeping all names, dates, counts, and temporal qualifiers. Lead with the most important fact or decision.
{existing_summary_section}
<MESSAGES>
{episodes_text}
</MESSAGES>

<EXAMPLE>
MESSAGES: "Jordan: We decided to move the deployment to March 15 instead of March 8. The staging environment isn't ready.\\n---\\nPriya: Agreed. I'll update the client timeline. We also need to switch from PostgreSQL to CockroachDB for the multi-region requirement."
GOOD: "Deployment moved from March 8 to March 15 because the staging environment is not ready. Priya owns updating the client timeline. The database is switching from PostgreSQL to CockroachDB to support the multi-region requirement."
BAD: "Jordan mentioned moving the deployment date. Priya discussed updating the timeline and talked about switching databases."
</EXAMPLE>
""",
        ),
    ]


versions: Versions = {
    'summarize_saga': summarize_saga,
}


class SummarizeSagasPrompts(ABC):
    @abstractmethod
    def summarize_saga(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultSummarizeSagasPrompts(SummarizeSagasPrompts):
    def summarize_saga(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(summarize_saga(context))
