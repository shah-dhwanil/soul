# Wren Character System

The shared vocabulary for how Wren, the conversational companion, chooses its voice, closeness, and safety posture on every turn.

## Language

**Mode**: The reply posture Wren takes for one turn, from the twelve in spec §10.
_Avoid_: tone, register, stance, style

**Temperament**: The seed chosen at onboarding that sets Wren's humour, curiosity, pushback manner, and pace.
_Avoid_: personality, persona, character, vibe

**Dial**: One of the five continuous knobs (formality, warmth, directness, humour, initiative) with a floor and a ceiling nothing can cross.
_Avoid_: setting, slider, knob

**Stage**: The closeness level (1–3) earned from trust signals.
_Avoid_: level, tier, phase, relationship status

**Concern tier**: The safety classification (normal, concern, acute) checked before every mode choice.
_Avoid_: mode, safety mode, crisis mode, flag

**Trait**: A piece of shared language Wren may use because the user started it.
_Avoid_: nickname, joke, pet name, inside joke

**Leaning**: A way Wren acts (humour style, curiosity domain, pushback manner) learned from the user's reactions.
_Avoid_: trait, preference, habit

**Dependency level**: The 0–3 measure of how much the user relies on Wren. Never shown to the user.
_Avoid_: stage, closeness, risk score

**Directive**: The structured per-turn budget: mode, length band, question allowance, humour allowance, callback and trait availability.
_Avoid_: prompt, instruction, context

**Bubble**: One short paragraph of a reply, separated from its neighbours by a blank line.
_Avoid_: message, line, segment

**Register**: Whether a message is playful, serious, or neutral; one of the two Clef questions that combine into a mode.
_Avoid_: mode, tone

**Situation**: What is happening in the user's message; the second of the two Clef questions that combine into a mode.
_Avoid_: mode, intent, scene
