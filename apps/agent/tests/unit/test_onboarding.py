from agent.services.onboarding import first_line_for, onboarding_samples


def _straight(text: str) -> str:
    # The §6 lines use typographic apostrophes; compare ignoring that difference.
    return text.replace("\u2019", "'")


def test_two_contrasting_samples_are_offered():
    samples = onboarding_samples()
    assert len(samples) == 2
    assert samples[0].temperament_id != samples[1].temperament_id
    assert all(s.sample_reply for s in samples)


def test_first_lines_are_distinct_and_verbatim():
    lines = {seed: first_line_for(seed) for seed in ("steady", "wry", "gentle", "tinker")}
    assert len(set(lines.values())) == 4
    assert _straight(lines["steady"]).startswith("I'm Wren, an AI that remembers what you tell it")
    assert _straight(lines["wry"]).startswith("I'm Wren, an AI.")


def test_unknown_seed_falls_back_to_steady():
    assert first_line_for("nope") == first_line_for("steady")
