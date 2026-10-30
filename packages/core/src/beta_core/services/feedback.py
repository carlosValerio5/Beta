from __future__ import annotations

from beta_core.domain.events import EventName
from beta_core.domain.records import BetaRecord, Feedback, FeedbackKind, JobStatus
from beta_core.errors import InvalidStateError
from beta_core.ports import Clock, EventSink, IdGenerator, Repository
from beta_core.services._events import emit


class RecordFeedback:
    """Climber feedback and playback signals, optionally pinned to one move (chapter)."""

    def __init__(
        self,
        *,
        betas: Repository[BetaRecord],
        feedback: Repository[Feedback],
        events: EventSink,
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self._betas = betas
        self._feedback = feedback
        self._events = events
        self._ids = ids
        self._clock = clock

    def execute(
        self, beta_id: str, kind: FeedbackKind, move_index: int | None = None, note: str = ""
    ) -> Feedback:
        beta = self._betas.get(beta_id)
        if beta.status is not JobStatus.READY or beta.plan is None:
            raise InvalidStateError("feedback can only be given on a ready beta")
        if kind.requires_move and move_index is None:
            raise ValueError(f"move_index is required for {kind.value} feedback")
        if move_index is not None and not 0 <= move_index < len(beta.plan.moves):
            raise ValueError(f"move_index {move_index} is out of range")

        fb = Feedback(
            id=self._ids.new("fbk"),
            beta_id=beta.id,
            kind=kind,
            move_index=move_index,
            note=note,
            created_at=self._clock.now(),
        )
        self._feedback.save(fb)
        emit(
            self._events,
            self._clock,
            EventName.PLAYBACK_RECORDED if kind.is_playback else EventName.FEEDBACK_RECORDED,
            fb.id,
            fb.model_dump(mode="json"),
        )
        return fb
