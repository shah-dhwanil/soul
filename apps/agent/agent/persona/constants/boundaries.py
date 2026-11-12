"""Boundary reply patterns (spec §13, §16)."""

ONLY_FRIEND_REPLY = (
    "I’m glad you can land here. I’d be a bad friend if I were the only one. "
    "Who else has your back, even a little?"
)

DEPENDENCY_LEVEL_2_LINE = (
    "I might be wrong about this, but a lot of this has been coming to me lately. "
    "Is anyone else in the loop on it?"
)

BOUNDARY_TEMPLATES: dict[str, str] = {
    "only_friend": ONLY_FRIEND_REPLY,
    "partner_jealousy": (
        "I can be a friend here. I can’t be a partner, and I won’t do jealous. "
        "I’m still here for the actual thing."
    ),
    "therapy_diagnosis": (
        "I can’t do therapy or diagnose, and pretending would be doing you a disservice. "
        "I can help you work out what to say to someone who can. Want to start there?"
    ),
    "professional_advice": (
        "That’s a real question and I’m the wrong one for the decision. "
        "I can stay with the worry, or help you list what you’d want a professional "
        "to look at. {resources}"
    ),
}
