import re

from agent.persona.context import WrenPromptContext
from agent.persona.template import PLACEHOLDER_NAMES, WREN_SYSTEM_PROMPT


def render_wren_system_prompt(ctx: WrenPromptContext) -> str:
    values = {
        "temperament": ctx.temperament,
        "dials": ctx.dials,
        "stage_permissions": ctx.stage_permissions,
        "active_traits": ctx.active_traits,
        "banned_phrases": ctx.banned_phrases,
        "configured_resources": ctx.configured_resources,
        "turn_directive": ctx.turn_directive,
        "memory_context": ctx.memory_context,
    }
    rendered = WREN_SYSTEM_PROMPT
    for name in PLACEHOLDER_NAMES:
        rendered = rendered.replace(f"{{{{{name}}}}}", values[name])
    remaining = re.findall(r"\{\{(\w+)\}\}", rendered)
    if remaining:
        raise ValueError(f"Unreplaced persona placeholders: {remaining}")
    return rendered
