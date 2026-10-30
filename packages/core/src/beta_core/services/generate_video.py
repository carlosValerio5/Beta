from __future__ import annotations

from beta_core.domain.climber import BodyModel
from beta_core.domain.events import EventName
from beta_core.domain.motion import ImageRef, MotionSpec
from beta_core.domain.records import Analysis, BetaRecord, JobStatus, VideoRecord, VideoStatus
from beta_core.domain.violations import Violation
from beta_core.errors import BetaError, InvalidStateError
from beta_core.ports import (
    Clock,
    EventSink,
    IdGenerator,
    MarkRenderer,
    MediaStore,
    MotionDirector,
    MotionRequest,
    Repository,
    VideoRenderer,
)
from beta_core.services._events import emit
from beta_core.services.generate_beta import load_image
from beta_core.validation import MotionSpecValidator, is_valid

DEFAULT_MAX_REPAIRS = 1


class RequestVideo:
    def __init__(
        self,
        *,
        betas: Repository[BetaRecord],
        videos: Repository[VideoRecord],
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self._betas = betas
        self._videos = videos
        self._ids = ids
        self._clock = clock

    def execute(self, beta_id: str) -> VideoRecord:
        beta = self._betas.get(beta_id)
        if beta.status is not JobStatus.READY or beta.plan is None:
            raise InvalidStateError("a video can only be made for a ready beta")
        now = self._clock.now()
        record = VideoRecord(
            id=self._ids.new("vid"),
            beta_id=beta.id,
            status=VideoStatus.DIRECTING,
            created_at=now,
            updated_at=now,
        )
        self._videos.save(record)
        return record


class ProduceVideo:
    """Direct → validate → repair → render. Without a renderer the video stops at DIRECTED."""

    def __init__(
        self,
        *,
        videos: Repository[VideoRecord],
        betas: Repository[BetaRecord],
        analyses: Repository[Analysis],
        media: MediaStore,
        director: MotionDirector,
        validator: MotionSpecValidator,
        renderer: VideoRenderer | None,
        events: EventSink,
        clock: Clock,
        marks: MarkRenderer | None = None,
        max_repairs: int = DEFAULT_MAX_REPAIRS,
    ) -> None:
        self._videos = videos
        self._betas = betas
        self._analyses = analyses
        self._media = media
        self._director = director
        self._validator = validator
        self._renderer = renderer
        self._events = events
        self._clock = clock
        self._marks = marks
        self._max_repairs = max_repairs

    def execute(self, video_id: str) -> VideoRecord:  # noqa: PLR0911 - one exit per failure mode
        record = self._videos.get(video_id)
        if record.status is not VideoStatus.DIRECTING:
            return record
        beta = self._betas.get(record.beta_id)
        analysis = self._analyses.get(beta.analysis_id)
        plan, problem = beta.plan, analysis.problem
        if plan is None or problem is None:
            return self._fail(record, error="beta or problem missing", attempts=0)

        image = load_image(self._media, analysis)
        if self._marks is not None:
            image = self._marks.render_marks(image, problem.holds)
        image_ref = ImageRef(
            uri=analysis.image.key, width=analysis.image.width, height=analysis.image.height
        )

        previous: MotionSpec | None = None
        violations: tuple[Violation, ...] = ()
        spec: MotionSpec | None = None
        attempts = 0
        for attempts in range(1, self._max_repairs + 2):
            request = MotionRequest(
                beta=plan,
                problem=problem,
                image=image,
                image_ref=image_ref,
                body=BodyModel.from_profile(beta.profile),
                px_per_cm=analysis.px_per_cm,
                previous_spec=previous,
                previous_violations=violations,
            )
            try:
                candidate = self._director.direct(request)
            except BetaError as exc:
                return self._fail(record, error=f"{type(exc).__name__}: {exc}", attempts=attempts)
            found = self._validator.validate(candidate, plan)
            if is_valid(found):
                spec = candidate
                break
            previous, violations = candidate, tuple(found)
        if spec is None:
            return self._fail(
                record,
                error="motion spec failed validation",
                attempts=attempts,
                violations=violations,
            )

        directed = record.model_copy(
            update={
                "status": VideoStatus.DIRECTED if self._renderer is None else VideoStatus.RENDERING,
                "spec": spec,
                "attempts": attempts,
                "updated_at": self._clock.now(),
            }
        )
        self._videos.save(directed)
        emit(
            self._events,
            self._clock,
            EventName.VIDEO_DIRECTED,
            record.id,
            {"beta_id": beta.id, "attempts": attempts, "spec": spec.model_dump(mode="json")},
        )
        if self._renderer is None:
            return directed

        try:
            result = self._renderer.render(spec, record.id)
        except BetaError as exc:
            return self._fail(directed, error=f"{type(exc).__name__}: {exc}", attempts=attempts)
        ready = directed.model_copy(
            update={
                "status": VideoStatus.READY,
                "video_key": result.video_key,
                "poster_key": result.poster_key,
                "duration_s": result.duration_s,
                "updated_at": self._clock.now(),
            }
        )
        self._videos.save(ready)
        emit(
            self._events,
            self._clock,
            EventName.VIDEO_RENDERED,
            record.id,
            {"beta_id": beta.id, **result.model_dump(mode="json")},
        )
        return ready

    def _fail(
        self,
        record: VideoRecord,
        *,
        error: str,
        attempts: int,
        violations: tuple[Violation, ...] = (),
    ) -> VideoRecord:
        failed = record.model_copy(
            update={
                "status": VideoStatus.FAILED,
                "error": error,
                "attempts": attempts,
                "violations": violations,
                "updated_at": self._clock.now(),
            }
        )
        self._videos.save(failed)
        emit(
            self._events,
            self._clock,
            EventName.VIDEO_FAILED,
            record.id,
            {
                "beta_id": record.beta_id,
                "error": error,
                "attempts": attempts,
                "violations": [v.model_dump(mode="json") for v in violations],
            },
        )
        return failed
