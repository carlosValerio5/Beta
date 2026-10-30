from __future__ import annotations

from collections.abc import Sequence

from beta_core.domain.events import EventName
from beta_core.domain.holds import Problem
from beta_core.domain.records import Analysis
from beta_core.errors import InvalidStateError
from beta_core.ports import Clock, EventSink, Repository
from beta_core.services._events import emit


class SelectProblem:
    """The climber picks which detected holds form the problem (by colour or explicit IDs)."""

    def __init__(self, *, analyses: Repository[Analysis], events: EventSink, clock: Clock) -> None:
        self._analyses = analyses
        self._events = events
        self._clock = clock

    def execute(
        self,
        analysis_id: str,
        *,
        start_hold_ids: Sequence[int],
        top_hold_id: int,
        hold_ids: Sequence[int] | None = None,
        color: str | None = None,
    ) -> Analysis:
        analysis = self._analyses.get(analysis_id)
        if hold_ids is None and color is None:
            raise InvalidStateError("select the problem's holds by hold_ids or by color")
        for hold_id in [*start_hold_ids, top_hold_id, *(hold_ids or [])]:
            analysis.hold(hold_id)  # raises UnknownHoldError

        chosen = (
            set(hold_ids)
            if hold_ids is not None
            else {h.id for h in analysis.holds if h.color == color}
        )
        chosen |= {*start_hold_ids, top_hold_id}
        problem = Problem(
            holds=tuple(h for h in analysis.holds if h.id in chosen),
            start_hold_ids=tuple(start_hold_ids),
            top_hold_id=top_hold_id,
            color=color,
        )
        updated = analysis.model_copy(update={"problem": problem})
        self._analyses.save(updated)
        emit(
            self._events,
            self._clock,
            EventName.PROBLEM_SELECTED,
            analysis.id,
            {
                "problem": problem.model_dump(mode="json"),
                "selection": "color" if hold_ids is None else "ids",
            },
        )
        return updated
