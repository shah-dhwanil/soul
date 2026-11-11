import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent.config import Settings
from agent.history import ChatTurn
from agent.model.memory_queries import (
    MEMORY_QUERY_SYSTEM,
    build_memory_query_user_prompt,
    parse_memory_query_response,
)
from agent.persona import WrenPromptContext, render_wren_system_prompt
from agent.persona.context import build_generation_user_prompt

logger = logging.getLogger(__name__)


class QueryLLM:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_agent_model,
            temperature=0.4,
        )
        self._gen = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_agent_model,
            temperature=0.85,
        )

    async def get_queries(
        self, current_chat: str, chat_history: list[ChatTurn]
    ) -> list[str]:
        history_text = "\n".join(
            f"user: {t.user_message}\nassistant: {t.agent_response}"
            for t in chat_history
        )
        user_prompt = build_memory_query_user_prompt(current_chat, history_text)
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=MEMORY_QUERY_SYSTEM),
                HumanMessage(content=user_prompt),
            ]
        )
        queries = parse_memory_query_response(str(response.content))
        logger.info(
            "memory_queries message=%r history_turns=%d queries=%s",
            current_chat[:80],
            len(chat_history),
            queries,
        )
        return queries

    async def generate_response(
        self,
        current_chat: str,
        chat_history: list[ChatTurn],
        *,
        persona: WrenPromptContext,
    ) -> str:
        system = render_wren_system_prompt(persona)
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=system),
        ]
        for turn in chat_history:
            messages.append(HumanMessage(content=turn.user_message))
            messages.append(AIMessage(content=turn.agent_response))
        messages.append(
            HumanMessage(
                content=build_generation_user_prompt(
                    current_chat,
                    turn_directive=persona.turn_directive,
                    memory_context=persona.memory_context,
                )
            )
        )
        response = await self._gen.ainvoke(messages)
        return str(response.content).strip()
