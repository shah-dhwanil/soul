"""Wire the minimized prompts in ``graphiti_prompts/`` into Graphiti via LLMPromptOverrides."""

import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from graphiti_core.llm_client.prompt_config import LLMPromptOverrides
from graphiti_core.prompts.models import ChatPrompt

# group name -> module in graphiti_prompts (eval prompts are intentionally not overridden)
_GROUPS = (
    "extract_nodes",
    "dedupe_nodes",
    "extract_edges",
    "extract_nodes_and_edges",
    "dedupe_edges",
    "summarize_nodes",
    "summarize_sagas",
)

_REPO_ROOT = Path(__file__).resolve().parents[5]


def _as_override(fn: Callable[[dict[str, Any]], list]) -> Callable[[dict[str, Any]], ChatPrompt]:
    """Adapt a ``list[Message]`` builder to the ``ChatPrompt`` builder Graphiti expects."""

    def _build(context: dict[str, Any]) -> ChatPrompt:
        return ChatPrompt.from_messages(fn(context))

    return _build


def build_prompt_overrides() -> LLMPromptOverrides:
    """Build LLMPromptOverrides from the minimized prompt modules."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    groups: dict[str, Any] = {}
    for group in _GROUPS:
        module = importlib.import_module(f"graphiti_prompts.{group}")
        nested_cls = getattr(LLMPromptOverrides, "".join(p.capitalize() for p in group.split("_")))
        groups[group] = nested_cls(
            **{name: _as_override(fn) for name, fn in module.versions.items()}
        )
    return LLMPromptOverrides(**groups)
