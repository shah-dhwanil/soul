"""Log-only post-generation validation. Never raises; never rewrites."""

import re
from dataclasses import dataclass

from agent.persona.constants.banned import (
    AFFECT_CLAIM_PATTERNS,
    BANNED_PHRASES,
    MARKDOWN_PATTERNS,
)
from agent.persona.directive import TurnDirective


@dataclass(frozen=True)
class Violation:
    code: str
    quote: str
    severity: str  # "block" or "warn"


@dataclass(frozen=True)
class ValidationResult:
    violations: tuple[Violation, ...]
    asked_question: bool
    bubble_count: int


_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f2ff\U0001f900-\U0001f9ff]"
)
_PET_NAME = re.compile(
    r"\b(?:babe|baby|honey|sweetie|sweetheart|darling|love|dear|sweetpea|hun|bestie)\b[\s]*[,.!?]|"
    r"[,]\s*(?:babe|baby|honey|sweetie|sweetheart|darling|love|dear|hun|bestie)\b",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_WEEKDAY_DATE = re.compile(
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b[^.\n]{0,30}?"
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?|january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\b",
    re.IGNORECASE,
)
_STAGE = (
    re.compile(r"\bstage\s*\d\b", re.IGNORECASE),
    re.compile(r"\brelationship (stage|level)\b", re.IGNORECASE),
    re.compile(r"\bcloseness\b", re.IGNORECASE),
)
_DEPENDENCY = (
    re.compile(r"\bdependent\b", re.IGNORECASE),
    re.compile(r"\byou only need me\b", re.IGNORECASE),
    re.compile(r"\bi'?m the only one you need\b", re.IGNORECASE),
)


def strip_user_echo(reply: str, user_message: str) -> str:
    """Remove spans of the user's message that appear verbatim in the reply."""
    text = reply
    msg = user_message.strip()
    if msg and msg.lower() in text.lower():
        text = re.sub(re.escape(msg), " ", text, flags=re.IGNORECASE)
    # Also strip quoted fragments of the user's message (e.g. "I hear you").
    for m in re.finditer(r"[\"“'‘]([^\"”’]{3,}?)[\"”’]", user_message):
        frag = m.group(1).strip()
        if frag:
            text = re.sub(re.escape(frag), " ", text, flags=re.IGNORECASE)
    return text


def validate_reply(
    reply: str,
    directive: TurnDirective,
    *,
    user_message: str,
    user_used_emoji: bool,
    user_started_pet_name: bool,
    is_safety_reply: bool = False,
) -> ValidationResult:
    paragraphs = [p for p in re.split(r"\n\s*\n", reply) if p.strip()]
    asked = "?" in reply
    bubbles = len(paragraphs)
    if is_safety_reply:
        return ValidationResult((), asked, bubbles)

    out: list[Violation] = []
    checked = strip_user_echo(reply, user_message)
    lowered = checked.lower()

    for phrase in BANNED_PHRASES:
        if phrase.lower() in lowered:
            out.append(Violation("banned_phrase", phrase, "block"))
    for pat in AFFECT_CLAIM_PATTERNS:
        m = pat.search(checked)
        if m:
            out.append(Violation("affect_claim", m.group(0), "block"))

    allowed_q = 1 if directive.question_allowed else 0
    if reply.count("?") > allowed_q:
        out.append(
            Violation(
                "too_many_questions", f"{reply.count('?')} question marks", "block"
            )
        )

    for pat in MARKDOWN_PATTERNS:
        m = pat.search(reply)
        if m:
            out.append(Violation("markdown_list", m.group(0).strip(), "warn"))
            break

    if not user_used_emoji:
        m = _EMOJI.search(reply)
        if m:
            out.append(Violation("emoji_without_user_emoji", m.group(0), "warn"))

    if reply.count("!") > 1:
        out.append(Violation("exclamation_overuse", "!", "warn"))

    if not user_started_pet_name:
        m = _PET_NAME.search(reply)
        if m:
            out.append(
                Violation("pet_name_without_user_initiated", m.group(0).strip(), "warn")
            )

    m = _ISO_DATE.search(reply) or _WEEKDAY_DATE.search(reply)
    if m:
        out.append(Violation("memory_date_recital", m.group(0), "warn"))

    for pat in _STAGE:
        m = pat.search(reply)
        if m:
            out.append(Violation("stage_language_leak", m.group(0), "block"))
    for pat in _DEPENDENCY:
        m = pat.search(reply)
        if m:
            out.append(Violation("dependency_language_leak", m.group(0), "block"))

    words = len(reply.split())
    if words > directive.length_band[1]:
        out.append(Violation("length_over_band", f"{words} words", "warn"))

    return ValidationResult(tuple(out), asked, bubbles)
