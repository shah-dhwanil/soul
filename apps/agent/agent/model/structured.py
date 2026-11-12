from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from agent.config import Settings


class StructuredOutputError(Exception):
    """Raised when a structured LLM call cannot produce a valid response."""


def make_structured_llm(settings: Settings) -> Any:
    """Build the Groq chat model used for detectors (temperature 0)."""
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_agent_model,
            temperature=0,
            api_key=settings.groq_api_key,
        )
    except Exception as exc:  # noqa: BLE001
        raise StructuredOutputError(f"could not build structured llm: {exc}") from exc


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)


async def async_structured_call(
    *,
    llm: Any,
    system: str,
    user: str,
    response_model: type[BaseModel],
) -> BaseModel:
    """Call ``llm`` for strict JSON-schema output and validate it.

    Retries once on invalid JSON / schema mismatch. Only ever raises
    ``StructuredOutputError``.
    """
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "strict": True,
            "schema": response_model.model_json_schema(),
        },
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            msg = await llm.ainvoke(messages, response_format=response_format)
            text = _content_to_text(msg.content)
            return response_model.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            last_error = exc
        except Exception as exc:  # noqa: BLE001
            raise StructuredOutputError(f"structured call failed: {exc}") from exc

    raise StructuredOutputError(
        f"invalid structured output after retry: {last_error}"
    ) from last_error
