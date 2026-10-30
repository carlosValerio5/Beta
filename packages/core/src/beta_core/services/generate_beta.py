from __future__ import annotations

from beta_core.domain.beta import BetaPlan
from beta_core.domain.climber import BodyModel, ClimberProfile
from beta_core.domain.events import EventName
from beta_core.domain.records import Analysis, BetaRecord, JobStatus
from beta_core.domain.violations import Violation
from beta_core.errors import BetaError, InvalidStateError
from beta_core.ports import (
    BetaPlanner,
    BetaRequest,
    Clock,
    EventSink,
    IdGenerator,
    MarkRenderer,
    MediaStore,
    NormalizedImage,
    Repository,
)
from beta_core.services._events import emit
from beta_core.validation import BetaValidator, is_valid

DEFAULT_MAX_REPAIRS = 2


def load_image(media: MediaStore, analysis: Analysis) -> NormalizedImage:
    return NormalizedImage(
        data=media.get(analysis.image.key),
        width=analysis.image.width,
        height=analysis.image.height,
        sha256=analysis.image.sha256,
        dhash=analysis.image.dhash,
    )


class RequestBeta:
    """Create a pending beta for an analysis whose problem has been selected (ADR-0008)."""

    def __init__(
        self,
        *,
        analyses: Repository[Analysis],
        betas: Repository[BetaRecord],
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self._analyses = analyses
        self._betas = betas
        self._ids = ids
        self._clock = clock

    def execute(self, analysis_id: str, profile: ClimberProfile) -> BetaRecord:
        analysis = self._analyses.get(analysis_id)
        if analysis.problem is None:
            raise InvalidStateError("select a problem before requesting a beta")
        now = self._clock.now()
        record = BetaRecord(
            id=self._ids.new("bet"),
            analysis_id=analysis.id,
            profile=profile,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._betas.save(record)
        return record


class ProduceBeta:
    """Plan → validate → repair (up to ``max_repairs`` times) → ready | failed."""

    def __init__(
        self,
        *,
        analyses: Repository[Analysis],
        betas: Repository[BetaRecord],
        media: MediaStore,
        marks: MarkRenderer,
        planner: BetaPlanner,
        validator: BetaValidator,
        events: EventSink,
        clock: Clock,
        max_repairs: int = DEFAULT_MAX_REPAIRS,
    ) -> None:
        self._analyses = analyses
        self._betas = betas
        self._media = media
        self._marks = marks
        self._planner = planner
        self._validator = validator
        self._events = events
        self._clock = clock
        self._max_repairs = max_repairs

    def execute(self, beta_id: str) -> BetaRecord:
        record = self._betas.get(beta_id)
        if record.status is not JobStatus.PENDING:
            return record
        analysis = self._analyses.get(record.analysis_id)
        problem = analysis.problem
        if problem is None:
            return self._fail(record, attempts=0, error="analysis has no selected problem")

        marked = self._marks.render_marks(load_image(self._media, analysis), problem.holds)
        body = BodyModel.from_profile(record.profile)
        previous: BetaPlan | None = None
        violations: tuple[Violation, ...] = ()
        attempts = 0
        for attempts in range(1, self._max_repairs + 2):
            request = BetaRequest(
                plan_id=record.id,
                analysis_id=analysis.id,
                problem=problem,
                image=marked,
                profile=record.profile,
                body=body,
                px_per_cm=analysis.px_per_cm,
                previous_attempt=previous,
                previous_violations=violations,
            )
            try:
                plan = self._planner.plan(request)
            except BetaError as exc:
                return self._fail(record, attempts=attempts, error=f"{type(exc).__name__}: {exc}")
            plan = plan.model_copy(update={"id": record.id, "analysis_id": analysis.id})
            found = self._validator.validate(plan, problem, body=body, px_per_cm=analysis.px_per_cm)
            if is_valid(found):
                return self._ready(record, plan, attempts, tuple(found))
            previous, violations = plan, tuple(found)
        return self._fail(
            record, attempts=attempts, error="beta failed validation", violations=violations
        )

    def _ready(
        self, record: BetaRecord, plan: BetaPlan, attempts: int, warnings: tuple[Violation, ...]
    ) -> BetaRecord:
        ready = record.model_copy(
            update={
                "status": JobStatus.READY,
                "plan": plan,
                "attempts": attempts,
                "violations": warnings,
                "updated_at": self._clock.now(),
            }
        )
        self._betas.save(ready)
        emit(
            self._events,
            self._clock,
            EventName.BETA_GENERATED,
            record.id,
            {
                "analysis_id": record.analysis_id,
                "profile": record.profile.model_dump(mode="json"),
                "plan": plan.model_dump(mode="json"),
                "attempts": attempts,
            },
        )
        return ready

    def _fail(
        self,
        record: BetaRecord,
        *,
        attempts: int,
        error: str,
        violations: tuple[Violation, ...] = (),
    ) -> BetaRecord:
        failed = record.model_copy(
            update={
                "status": JobStatus.FAILED,
                "attempts": attempts,
                "error": error,
                "violations": violations,
                "updated_at": self._clock.now(),
            }
        )
        self._betas.save(failed)
        emit(
            self._events,
            self._clock,
            EventName.BETA_FAILED,
            record.id,
            {
                "analysis_id": record.analysis_id,
                "attempts": attempts,
                "error": error,
                "violations": [v.model_dump(mode="json") for v in violations],
            },
        )
        return failed
