import re

from agent.persona.context import WrenPromptContext
from agent.persona.loader import load_persona
from agent.persona.template import PLACEHOLDER_NAMES


def render_wren_system_prompt(ctx: WrenPromptContext) -> str:
    values = {
        "temperament": ctx.temperament,
        "dials": ctx.dials,
        "stage_permissions": ctx.stage_permissions,
        "active_traits": ctx.active_traits,
        "mode_block": "",
        "turn_directive": "",
        "banned_phrases": ctx.banned_phrases,
        "configured_resources": ctx.configured_resources,
    }
    rendered = load_persona().prompt
    for name in PLACEHOLDER_NAMES:
        rendered = rendered.replace(f"{{{{{name}}}}}", values[name])
    remaining = re.findall(r"\{\{(\w+)\}\}", rendered)
    if remaining:
        raise ValueError(f"Unreplaced persona placeholders: {remaining}")
    return rendered
