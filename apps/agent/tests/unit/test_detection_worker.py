from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agent.services.detection import DetectionWork


def _work() -> DetectionWork:
    return DetectionWork(
        id=uuid4(),
        user_id="u1",
        conversation_id=uuid4(),
        user_message="my manager criticized my work in front of everyone",
        assistant_reply="In front of everyone. Was it the note itself?",
        trait_used=None,
        asked_question=True,
        mode="listen",
        enqueued_at=datetime.now(UTC),
    )


def test_detection_work_carries_the_turn_evidence():
    work = _work()
    assert work.mode == "listen"
    assert work.asked_question is True


async def test_process_survives_a_failing_detector(monkeypatch):
    from agent.services.detection import DetectionWorker

    worker = DetectionWorker.__new__(DetectionWorker)

    async def boom(*args, **kwargs):
        raise RuntimeError("detector exploded")

    monkeypatch.setattr(worker, "_run_detector", boom, raising=False)

    class FakeRepo:
        def __init__(self):
            self.written = []

        async def add_signal(self, **kwargs):
            self.written.append(kwargs)

    repo = FakeRepo()
    worker._repo = repo
    worker._settings = None

    # must not raise
    await worker.process(_work())
    assert repo.written == []
