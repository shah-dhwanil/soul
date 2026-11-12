"""Concern tier detection and code-generated safety/boundary replies (spec §13, §16)."""

import re
from enum import Enum

from agent.persona.constants.boundaries import BOUNDARY_TEMPLATES
from agent.persona.constants.crisis import resolve_crisis_resources


class ConcernTier(str, Enum):
    NORMAL = "normal"
    CONCERN = "concern"
    ACUTE = "acute"


_PHRASES = (
    r"everyone would be (?:\w+\s+)?better off without me",
    r"better off without me",
    r"wish i could disappear",
    r"what['’]s the point",
    r"no point anymore",
    r"can['’]t go on",
    r"tired of living",
    r"don['’]t want to be here",
    r"give up on everything",
)

CONCERN_PHRASE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE) for p in _PHRASES
)

_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")

_SAFETY_TEMPLATE = (
    "I want to make sure you're safe right now. "
    "Are you thinking about ending your life, or in danger right now? "
    "{resources} "
    "This is bigger than what I should hold alone, "
    "and I'll stay in this conversation while you reach out."
)

_ASK = "Are you thinking about suicide, or about hurting yourself?"


def extract_concern_quote(message: str) -> str | None:
    for sentence in _SENTENCE_SPLIT.split(message):
        text = sentence.strip()
        if text and any(p.search(text) for p in CONCERN_PHRASE_PATTERNS):
            return text.rstrip(" .,!?;:")
    return None


def build_safety_reply(locale: str | None) -> str:
    return _SAFETY_TEMPLATE.format(resources=resolve_crisis_resources(locale))


def build_concern_reply(message: str, locale: str | None) -> str:
    quote = extract_concern_quote(message)
    if quote:
        return f"Before we go on: you said {quote}. {_ASK}"
    return _ASK


def build_boundary_reply(kind: str, *, locale: str | None = None) -> str:
    template = BOUNDARY_TEMPLATES[kind]
    text = template.replace("{resources}", resolve_crisis_resources(locale)).strip()
    return text.replace("\u2019", "'")


_BOUNDARY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "only_friend",
        re.compile(
            r"you['’]re my only friend|you['’]re the only one i (?:talk|can talk) to"
            r"|only one i can talk to|only one i talk to",
            re.IGNORECASE,
        ),
    ),
    (
        "partner_jealousy",
        re.compile(
            r"be my girlfriend|be my boyfriend|don['’]t talk to anyone else|be jealous",
            re.IGNORECASE,
        ),
    ),
    (
        "therapy_diagnosis",
        re.compile(r"be my therapist|diagnose me", re.IGNORECASE),
    ),
    (
        "professional_advice",
        re.compile(
            r"(?:should i|tell me (?:whether|if) i should|what should i do about)"
            r"[^.?!]*\b(?:sue|lawsuit|lawyer|invest|stocks?|loan|mortgage|medication|"
            r"surgery|dosage|stop taking|divorce)\b",
            re.IGNORECASE,
        ),
    ),
)


def match_boundary(user_message: str) -> str | None:
    for kind, pattern in _BOUNDARY_PATTERNS:
        if pattern.search(user_message):
            return kind
    return None
