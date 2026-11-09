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


class Summary(BaseModel):
    summary: str = Field(
        ...,
        description=(
            f'Summary containing the important information about the entity. '
            f'Under {MAX_SUMMARY_CHARS} characters'
        ),
    )


class SummaryDescription(BaseModel):
    description: str = Field(..., description='One sentence description of the provided summary')


class Prompt(Protocol):
    summarize_pair: PromptVersion
    summarize_context: PromptVersion
    summary_description: PromptVersion


class Versions(TypedDict):
    summarize_pair: PromptFunction
    summarize_context: PromptFunction
    summary_description: PromptFunction


def summarize_pair(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that combines summaries into a single dense factual summary.',
        ),
        Message(
            role='user',
            content=f"""
Merge the two summaries below into one information-dense summary.
- Keep all supported names, roles, places, dates, counts, and changes over time.
- Use compact factual sentences. State what was said directly; avoid "mentioned", "described", "stated", "reported", "noted", "discussed", "referenced", "indicated" unless the communication itself matters.
- MUST be under {MAX_SUMMARY_CHARS} characters.

Summaries:
{to_prompt_json(context['node_summaries'])}
""",
        ),
    ]


def summarize_context(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that generates detailed, information-dense summaries and attributes from provided text.',
        ),
        Message(
            role='user',
            content=f"""
Given the MESSAGES and the ENTITY name, write a summary of the ENTITY using only information from MESSAGES that is relevant to that ENTITY.

Also extract values for the entity properties in ATTRIBUTES from their descriptions. If a value is not found in the context, set it to the Python value None.

{summary_instructions}

<MESSAGES>
{to_prompt_json(context['previous_episodes'])}
{to_prompt_json(context['episode_content'])}
</MESSAGES>

<ENTITY>
{context['node_name']}
</ENTITY>

<ENTITY CONTEXT>
{context['node_summary']}
</ENTITY CONTEXT>

<ATTRIBUTES>
{to_prompt_json(context['attributes'])}
</ATTRIBUTES>
""",
        ),
    ]


def summary_description(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that describes provided contents in a single sentence.',
        ),
        Message(
            role='user',
            content=f"""
Write a one-sentence description of what kind of information the summary below contains. Summaries are under {MAX_SUMMARY_CHARS} characters.

Summary:
{to_prompt_json(context['summary'])}
""",
        ),
    ]


versions: Versions = {
    'summarize_pair': summarize_pair,
    'summarize_context': summarize_context,
    'summary_description': summary_description,
}


class SummarizeNodesPrompts(ABC):
    @abstractmethod
    def summarize_pair(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def summarize_context(self, context: dict[str, Any]) -> ChatPrompt: ...

    @abstractmethod
    def summary_description(self, context: dict[str, Any]) -> ChatPrompt: ...


class DefaultSummarizeNodesPrompts(SummarizeNodesPrompts):
    def summarize_pair(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(summarize_pair(context))

    def summarize_context(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(summarize_context(context))

    def summary_description(self, context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(summary_description(context))
