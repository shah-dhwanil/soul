from agent.model.detectors import DETECTORS


def test_all_six_detectors_exist():
    assert set(DETECTORS) == {
        "trust",
        "dependency",
        "trait_candidate",
        "trait_reaction",
        "leaning",
        "attunement",
    }


def test_trust_detector_names_all_six_signals():
    system = DETECTORS["trust"].system
    for signal in ("S1", "S2", "S3", "S4", "S5", "S6"):
        assert signal in system


def test_dependency_detector_names_all_six_signals():
    system = DETECTORS["dependency"].system
    for signal in ("D1", "D2", "D3", "D4", "D5", "D6"):
        assert signal in system


def test_attunement_detector_excludes_silence_as_shutdown():
    system = DETECTORS["attunement"].system.lower()
    assert "silence" in system
    assert "never" in system


def test_trait_detector_forbids_inventing_labels():
    system = DETECTORS["trait_candidate"].system.lower()
    assert "own words" in system or "user's own words" in system
