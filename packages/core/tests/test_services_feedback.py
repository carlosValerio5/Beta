import pytest

from beta_core.domain.events import EventName
from beta_core.domain.records import BetaRecord, Feedback, FeedbackKind, JobStatus
from beta_core.errors import InvalidStateError
from beta_core.services.feedback import RecordFeedback
from beta_core.testing import (
    FixedClock,
    InMemoryMediaStore,
    InMemoryRepository,
    RecordingEventSink,
    SequentialIds,
    ladder_analysis,
    ladder_beta_record,
)


@pytest.fixture
def env() -> dict:  # type: ignore[type-arg]
    betas = InMemoryRepository[BetaRecord]()
    beta = ladder_beta_record(ladder_analysis(InMemoryMediaStore()))
    betas.save(beta)
    feedback = InMemoryRepository[Feedback]()
    events = RecordingEventSink()
    use_case = RecordFeedback(
        betas=betas, feedback=feedback, events=events, ids=SequentialIds(), clock=FixedClock()
    )
    return {"betas": betas, "beta": beta, "feedback": feedback, "events": events, "uc": use_case}


def test_records_move_feedback(env: dict) -> None:  # type: ignore[type-arg]
    fb = env["uc"].execute(env["beta"].id, FeedbackKind.MOVE_LOOKS_WRONG, move_index=2, note="Too far")
    assert env["feedback"].get(fb.id) == fb
    assert env["events"].names() == [EventName.FEEDBACK_RECORDED]


def test_playback_kinds_emit_playback_event(env: dict) -> None:  # type: ignore[type-arg]
    env["uc"].execute(env["beta"].id, FeedbackKind.REWATCH, move_index=1)
    assert env["events"].names() == [EventName.PLAYBACK_RECORDED]


def test_rejects_move_index_out_of_range(env: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError, match="move_index"):
        env["uc"].execute(env["beta"].id, FeedbackKind.MOVE_LOOKS_WRONG, move_index=99)


def test_move_kinds_require_move_index(env: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError, match="move_index"):
        env["uc"].execute(env["beta"].id, FeedbackKind.MOVE_LOOKS_WRONG)


def test_rejects_feedback_on_unfinished_beta(env: dict) -> None:  # type: ignore[type-arg]
    env["betas"].save(env["beta"].model_copy(update={"status": JobStatus.PENDING, "plan": None}))
    with pytest.raises(InvalidStateError):
        env["uc"].execute(env["beta"].id, FeedbackKind.SENT)
