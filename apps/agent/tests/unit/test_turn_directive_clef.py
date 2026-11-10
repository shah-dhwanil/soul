from agent.persona.context import build_turn_directive
from tests.unit.test_clef_flash_parsing import CLEF_FLASH_GUJARATI_TURN


def test_turn_directive_includes_clef_emotion_labels() -> None:
    directive = build_turn_directive({"raw": CLEF_FLASH_GUJARATI_TURN})
    assert "neutral" in directive
    assert "direct" in directive
