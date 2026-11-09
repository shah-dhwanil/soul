import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent.config import Settings
from agent.history import ChatTurn


class QueryLLM:
    def __init__(self, settings: Settings) -> None:
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
        prompt = (
            "Return a JSON array of 1 to 3 short search queries for a knowledge "
            "graph. Use entities and events from context; do not invent names.\n"
            f"Recent chat:\n{history_text}\n"
            f"Current user message: {current_chat}"
        )
        response = await self._llm.ainvoke(
            [
                SystemMessage(content="Reply with JSON only: [\"query\", ...]"),
                HumanMessage(content=prompt),
            ]
        )
        content = str(response.content).strip()
        match = re.search(r"\[[\s\S]*\]", content)
        if not match:
            return [current_chat[:200]]
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return [str(q) for q in parsed[:3] if q]
        except json.JSONDecodeError:
            pass
        return [current_chat[:200]]

    async def generate_response(
        self,
        current_chat: str,
        chat_history: list[ChatTurn],
        memories: list[dict[str, Any]],
        *,
        tone_hint: str | None = None,
    ) -> str:
        memory_block = "\n".join(
            f"- {m.get('fact', m)}" for m in memories
        ) or "(no memories retrieved)"
        tone = tone_hint or "warm and supportive"
        system = (
            "You are Wren, a close friend the user can talk things through with. "
            f"Target tone: {tone}.\n"
            f"Relevant memories:\n{memory_block}\n"
            "Reply in one or two short paragraphs. Do not use bullet lists."
        )
        messages: list[SystemMessage | HumanMessage] = [SystemMessage(content=system)]
        for turn in chat_history:
            messages.append(HumanMessage(content=turn.user_message))
            messages.append(
                HumanMessage(content=f"(assistant previously said: {turn.agent_response})")
            )
        messages.append(HumanMessage(content=current_chat))
        response = await self._gen.ainvoke(messages)
        return str(response.content).strip()
