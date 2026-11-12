import re

from agent.persona.constants.modes import Mode
from agent.persona.directive import TurnDirective, render_directive


def _directive(**overrides) -> TurnDirective:
    base = dict(  # noqa: C408
        mode=Mode.EVERYDAY,
        length_band=(3, 25),
        max_bubbles=3,
        question_allowed=True,
        advice_allowed=False,
        humor_allowed=True,
        callback_allowed=True,
        trait_allowed=False,
        concern_tier="normal",
        dependency_level=0,
        stage=1,
        closing_signal=False,
        reason_codes=(),
    )
    base.update(overrides)
    return TurnDirective(**base)


def test_directive_renders_prose_without_labels_or_digits():
    out = render_directive(_directive())
    assert out
    assert "mode:" not in out.lower()
    assert not re.search(r"\d", out)


def test_directive_renders_the_mode_name():
    out = render_directive(_directive(mode=Mode.LISTEN)).lower()
    assert "listen" in out or "stay with it" in out


def test_directive_marks_no_advice():
    out = render_directive(_directive(mode=Mode.LISTEN)).lower()
    assert "advice" in out or "advise" in out
