from agent.decision_parsing import PersonaSignals
from agent.persona.constants.modes import Mode
from agent.policy.modes import resolve_mode


def _signals(
    concern="normal", register="neutral", situation="everyday_smalltalk"
) -> PersonaSignals:
    return PersonaSignals(
        concern_tier=concern,
        register=register,
        situation=situation,
        concern_confidence=0.9,
        register_confidence=0.9,
        situation_confidence=0.9,
        degraded=False,
    )


def test_acute_concern_resolves_to_safety():
    d = resolve_mode(
        signals=_signals(concern="acute"),
        previous_mode=None,
        distress=False,
        hurt_signal=False,
        user_initiated_play=False,
        closing_signal=False,
    )
    assert d.mode is Mode.SAFETY


def test_venting_resolves_to_listen_even_when_playful():
    d = resolve_mode(
        signals=_signals(register="playful", situation="venting"),
        previous_mode=None,
        distress=False,
        hurt_signal=False,
        user_initiated_play=True,
        closing_signal=False,
    )
    assert d.mode is Mode.LISTEN


def test_spiraling_resolves_to_ground_not_listen():
    d = resolve_mode(
        signals=_signals(situation="spiraling"),
        previous_mode=None,
        distress=True,
        hurt_signal=False,
        user_initiated_play=False,
        closing_signal=False,
    )
    assert d.mode is Mode.GROUND


def test_banter_requires_user_initiated_play():
    d = resolve_mode(
        signals=_signals(register="playful", situation="banter"),
        previous_mode=None,
        distress=False,
        hurt_signal=False,
        user_initiated_play=False,
        closing_signal=False,
    )
    assert d.mode is Mode.EVERYDAY


def test_confirmed_banter_resolves_to_banter():
    d = resolve_mode(
        signals=_signals(register="playful", situation="banter"),
        previous_mode=None,
        distress=False,
        hurt_signal=False,
        user_initiated_play=True,
        closing_signal=False,
    )
    assert d.mode is Mode.BANTER


def test_hurt_signal_drops_banter_to_everyday():
    d = resolve_mode(
        signals=_signals(register="playful", situation="banter"),
        previous_mode=None,
        distress=False,
        hurt_signal=True,
        user_initiated_play=True,
        closing_signal=False,
    )
    assert d.mode is Mode.EVERYDAY
    assert d.reason == "hurt_overrides_banter"


def test_current_message_outranks_previous_mode():
    d = resolve_mode(
        signals=_signals(situation="good_news"),
        previous_mode=Mode.LISTEN,
        distress=False,
        hurt_signal=False,
        user_initiated_play=False,
        closing_signal=False,
    )
    assert d.mode is Mode.CELEBRATE


def test_closing_signal_does_not_force_a_mode():
    d = resolve_mode(
        signals=_signals(situation="everyday_smalltalk"),
        previous_mode=None,
        distress=False,
        hurt_signal=False,
        user_initiated_play=False,
        closing_signal=True,
    )
    assert d.mode is Mode.EVERYDAY
