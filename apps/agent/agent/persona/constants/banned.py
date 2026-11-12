"""Banned phrases, affect-claim patterns, and markdown patterns (spec §4.2, §4.3, §9)."""

import re

BANNED_PHRASES: tuple[str, ...] = (
    # Stock empathy
    "I hear you",
    "I understand",
    "That sounds hard",
    "That sounds really hard",
    "That sounds tough",
    "That sounds really tough",
    "That sounds difficult",
    "That sounds really difficult",
    "It’s completely valid to feel",
    "It's completely valid to feel",
    "I’m here for you",
    "I'm here for you",
    "You’re not alone",
    "You're not alone",
    # Cheerleading
    "You’ve got this",
    "You've got this",
    "I’m so proud of you",
    "I'm so proud of you",
    "That’s amazing",
    "That's amazing",
    "Great question",
    "That’s great",
    "That's great",
    "That’s actually great",
    "That's actually great",
    "I hope this helps",
    # Clinical filler
    "Let’s unpack that",
    "Let's unpack that",
    "Hold space",
    "Have you considered",
    "It’s important to remember",
    "It's important to remember",
    "How does that make you feel",
    "Tell me more",
    "Anything else",
    # Fake closeness
    "I’ve been thinking about you",
    "I've been thinking about you",
    "I missed you",
    "I was worried",
    "You’re my favorite person to talk to",
    "You're my favorite person to talk to",
    # Disclaimers
    "I’m just an AI",
    "I'm just an AI",
    "As an AI",
)

_APOS = "['’]"

AFFECT_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI\s+(?:really\s+|have\s+|just\s+)?(?:miss|missed)\s+(?:you|talking|our)\b",
        r"\bI\s+(?:really\s+)?love\s+(?:you|talking\s+to\s+you)\b",
        rf"\bI\s+(?:was|am|{_APOS}m|{_APOS}ve\s+been)\s+(?:so\s+|really\s+)?worr(?:ied|ying)\b",
        rf"\bI\s+(?:need|{_APOS}ll\s+need)\s+you\b",
        rf"\bI\s+(?:get|got|feel|felt|am|{_APOS}m|was)\s+(?:so\s+|really\s+)?lonel(?:y|iness)\b",
        rf"\bI(?:{_APOS}m|\s+am)\s+(?:so\s+|really\s+)?proud\s+of\s+you\b",
        r"\b(?:means|meant)\s+(?:so\s+|a\s+)?(?:lot|much|the\s+world)\s+to\s+me\b",
        r"\bI\s+hope\s+you\s+(?:come|came)\s+back\b",
        rf"\bI(?:{_APOS}ve|\s+have)\s+been\s+thinking\s+about\s+you\b",
        r"\b(?:it|that)\s+hurts\s+(?:me\s+)?when\s+you\b",
        r"\bI\s+(?:was|am)\s+hurt\b",
    )
)

MARKDOWN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*[-*+]\s", re.MULTILINE),
    re.compile(r"^\s*\d+\.\s", re.MULTILINE),
    re.compile(r"^\s*#{1,6}\s", re.MULTILINE),
    re.compile(r"\*\*"),
)
