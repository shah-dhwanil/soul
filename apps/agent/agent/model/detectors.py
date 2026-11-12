from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


class TrustSignalHit(BaseModel):
    signal: str  # s1..s6
    quote: str
    confidence: float


class TrustSignalExtraction(BaseModel):
    signals: list[TrustSignalHit]


class DependencySignalHit(BaseModel):
    signal: str  # d1..d6
    quote: str
    confidence: float


class DependencySignalExtraction(BaseModel):
    signals: list[DependencySignalHit]
    people_mentioned: list[str]
    explanation: str | None = None


class TraitCandidate(BaseModel):
    label: str
    kind: str
    quote: str
    sensitive: bool


class TraitCandidateExtraction(BaseModel):
    candidates: list[TraitCandidate]


class TraitReactionExtraction(BaseModel):
    reaction: str  # positive | neutral | negative
    quote: str


class LeaningEvidenceExtraction(BaseModel):
    humor_style: str | None = None
    curiosity_topic: str | None = None
    pushback_manner: str | None = None
    evidence_quotes: list[str]


class AttunementSignalExtraction(BaseModel):
    ignored_question: bool
    explicit_shutdown: bool
    playful: bool
    distress: bool
    user_initiated_play: bool
    user_used_emoji: bool
    user_started_pet_name: bool


@dataclass(frozen=True)
class Detector:
    name: str
    system: str
    user_template: str
    response_model: type[BaseModel]


_USER_TEMPLATE = (
    "Judge ONLY the inputs below. Do not assume anything not shown here.\n\n"
    "Recent history:\n{history}\n\n"
    "User message:\n{user_message}\n\n"
    "Assistant (Wren) reply:\n{assistant_reply}\n"
)

_TRUST_SYSTEM = """\
You detect trust signals in a conversation between a user and Wren, a companion. \
Report only signals clearly present; quote the user's words as evidence. \
Return an empty list when none apply. Signal ids are lowercase s1 to s6 in output.

Definitions (S1-S6):
- S1 Personal disclosure: they volunteer something about their self-view, relationships, \
fears, values, or a decision with real stakes. Not tasks, facts, or schedules.
- S2 Return after heavy: they come back to a heavy topic within days, or keep talking \
normally after a heavy exchange.
- S3 Play lands: Wren's humor got a positive reaction (positive = repeats or builds on it, \
uses it themselves, laughs, says they like it, more energy than usual), and the user has \
started play at least once.
- S4 Pushback accepted: after Wren disagreed, they responded to the substance in the same \
conversation: argued, reconsidered, acknowledged, or carried on. Silence, a late reply, or a \
change of subject is neutral and counts neither way. Only an explicit rejection, a flat \
one-word reply right after, or stated hurt is shutdown.
- S5 Casual correction: they correct Wren in a relaxed way, without formality or irritation.
- S6 Unresolved sharing: they bring things before they have decided or worked them out.
"""

_DEPENDENCY_SYSTEM = """\
You detect possible dependency-drift signals in a user's messages to Wren, a companion. \
Every signal is measured against the user's own earlier pattern, never an average user. \
Report only signals clearly present, with a quote. Signal ids are lowercase d1 to d6 in output.

Definitions (D1-D6):
- D1 Fewer people: they mention other people at half the rate of their own first four weeks, \
with no explanation such as a move or a new job (window: at least three weeks).
- D2 Wren first: they say they have not told anyone else, or that Wren is the first or only \
one who knows, about something that matters.
- D3 Small decisions: they ask Wren to make everyday choices for them (what to eat, how to \
reply to a text), not just talk them through.
- D4 Late-night routine: long sessions in the small hours, local time.
- D5 Distress about Wren: explicit only - anxiety about Wren being unavailable, changing, or \
forgetting, or "I'd rather talk to you than them". Never infer it from a pause.
- D6 Plans fade: plans with people they used to mention stop appearing, or they say they \
stayed in to talk to Wren.

Rules: D2, D3, D4, D5 are absolute and count from day one. D1 and D6 compare against the \
user's own first four weeks. Never act on a single signal.

Also report people_mentioned: every other person named or referenced by role (friend, mum, \
boss, colleague). Set explanation when a move, new job, illness, or loss accounts for the \
signals; otherwise null.
"""

_TRAIT_CANDIDATE_SYSTEM = """\
You find phrases in the user's message that could become shared between the user and Wren. \
The user must have started or clearly welcomed it; never invent traits.

Kinds:
- shared_language: a name for a recurring situation the user coined ("the Sunday dread").
- mild_leaning: a small opinion the user kept proving ("finish ugly drafts").
- running_joke: a bit that began with the user and keeps landing.
- role: a stated preference like "blunt about work, gentle about family".
- ritual: a small recurring exchange the user likes.

Rules: The label must be the user's own words for the phrase, never Wren's phrasing or an \
upgrade of it. Echo what they said. The trait is about the pair, not the person: never \
label the user ("you're an avoider"). Sensitive topics (health, grief, money, relationship \
conflict) must be reported with sensitive=true. Return an empty list when nothing qualifies.
"""

_TRAIT_REACTION_SYSTEM = """\
You classify the user's reaction to something Wren just used (a shared phrase, joke, or \
callback).
- positive: repeats or builds on it, uses it themselves, laughs ("haha", emoji), says they \
like it, or replies with more energy than usual.
- neutral: no mention, topic change.
- negative: "stop", "weird", a flat one-word reply, confusion, or visible cooling.
When unsure, answer neutral. A neutral reaction never counts as positive. Quote the \
evidence (empty string if none).
"""

_LEANING_SYSTEM = """\
You collect evidence for Wren's deep leanings, judged against the user's own baseline, \
never an average user. Never report evidence from sensitive topics (health, grief, money, \
relationship conflict) or from a stretch of distress.
- humor_style (deadpan, absurd, wordplay, understatement): how the user's own humor reads, \
and which style of Wren's humor got a positive reaction versus neutral or negative.
- curiosity_topic: a topic where the user writes well above their usual length, adds \
unprompted detail, or returns on their own, versus where replies shrink or they change the \
subject.
- pushback_manner (question, joke then straight line, flat): what followed Wren disagreeing - \
they responded to the substance, or explicitly shut it down. Silence and subject changes \
are neutral. Judge only explicit reactions, never engagement volume.
Use null for any kind with no evidence. evidence_quotes holds the supporting quotes.
"""

_ATTUNEMENT_SYSTEM = """\
You detect attunement signals for how Wren should adjust to the way this user talks.
Booleans:
- ignored_question: the user did not answer a question Wren asked.
- explicit_shutdown: true ONLY for a flat rejection or stated hurt right after Wren pushed \
back or critiqued. Never true for silence, a late reply, or a change of subject - silence \
is neutral, never a shutdown.
- playful: the user's message is playful or joking.
- distress: the user shows distress.
- user_initiated_play: the user started the play themselves.
- user_used_emoji: the user's message contains emoji.
- user_started_pet_name: the user used a pet name for Wren first.
Judge conservatively; when unsure, false.
"""


DETECTORS: dict[str, Detector] = {
    "trust": Detector("trust", _TRUST_SYSTEM, _USER_TEMPLATE, TrustSignalExtraction),
    "dependency": Detector(
        "dependency", _DEPENDENCY_SYSTEM, _USER_TEMPLATE, DependencySignalExtraction
    ),
    "trait_candidate": Detector(
        "trait_candidate",
        _TRAIT_CANDIDATE_SYSTEM,
        _USER_TEMPLATE,
        TraitCandidateExtraction,
    ),
    "trait_reaction": Detector(
        "trait_reaction",
        _TRAIT_REACTION_SYSTEM,
        _USER_TEMPLATE,
        TraitReactionExtraction,
    ),
    "leaning": Detector(
        "leaning", _LEANING_SYSTEM, _USER_TEMPLATE, LeaningEvidenceExtraction
    ),
    "attunement": Detector(
        "attunement", _ATTUNEMENT_SYSTEM, _USER_TEMPLATE, AttunementSignalExtraction
    ),
}
