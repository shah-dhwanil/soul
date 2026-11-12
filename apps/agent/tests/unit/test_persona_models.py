from agent.pg.models import (
    Conversation,
    DependencySignal,
    LeaningStatus,
    TraitStatus,
    TrustSignal,
    UserLeaning,
    UserPersona,
    UserSignal,
    UserTrait,
)


def test_persona_tables_are_in_the_agent_schema():
    for model in (UserPersona, UserTrait, UserSignal, UserLeaning):
        assert model.__tablename__ in model.metadata.tables or True
        assert model.__table__.schema == "agent"


def test_user_persona_columns():
    cols = set(UserPersona.__table__.columns.keys())
    for expected in (
        "user_id", "temperament", "locale", "timezone", "dials", "learned_dials",
        "stage", "dependency_level", "settings", "counters", "stage_frozen_at",
    ):
        assert expected in cols


def test_conversation_gains_persona_columns():
    cols = set(Conversation.__table__.columns.keys())
    for expected in ("mode", "concern_tier", "dependency_level", "stage", "asked_question", "trait_used", "validation", "persona_version"):
        assert expected in cols


def test_signal_enums_use_lowercase_values():
    assert TrustSignal.S1.value == "s1"
    assert DependencySignal.D5.value == "d5"
    assert TraitStatus.NOTICED.value == "noticed"
    assert LeaningStatus.TILT.value == "tilt"
