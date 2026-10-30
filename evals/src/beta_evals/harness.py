"""Run golden cases through the real pipeline (same use cases as the API) and score them."""

from __future__ import annotations

import time
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from beta_core.domain.climber import ClimberProfile
from beta_core.domain.records import Analysis, BetaRecord, JobStatus, VideoRecord, VideoStatus
from beta_core.ports import BetaPlanner, MotionDirector
from beta_core.services.analyze import AnalyzeBoulder
from beta_core.services.generate_beta import ProduceBeta, RequestBeta
from beta_core.services.generate_video import ProduceVideo, RequestVideo
from beta_core.services.select_problem import SelectProblem
from beta_core.testing import (
    FixedClock,
    InMemoryMediaStore,
    InMemoryRawImageSink,
    InMemoryRepository,
    RecordingEventSink,
    SequentialIds,
)
from beta_core.validation import BetaValidator, MotionSpecValidator
from beta_evals.golden import GoldenCase
from beta_evals.metrics import MATCH_DISTANCE_PX, CaseResult, detection_scores, summarise
from beta_vision.detect import ColorHoldDetector, match_holds
from beta_vision.overlay import PillowMarkRenderer
from beta_vision.preprocess import PillowPreprocessor

DEFAULT_PROFILE = ClimberProfile(height_cm=175)


class EvalReport(BaseModel):
    created_at: datetime
    planner: str
    director: str
    cases: list[CaseResult]
    summary: dict[str, float]
    thresholds: dict[str, float] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)


def run_eval(
    cases: Sequence[GoldenCase],
    planner: BetaPlanner,
    director: MotionDirector,
    profile: ClimberProfile = DEFAULT_PROFILE,
) -> EvalReport:
    results = [_run_case(case, planner, director, profile) for case in cases]
    return EvalReport(
        created_at=datetime.now(UTC),
        planner=planner.name,
        director=director.name,
        cases=results,
        summary=summarise(results),
    )


def _run_case(
    case: GoldenCase, planner: BetaPlanner, director: MotionDirector, profile: ClimberProfile
) -> CaseResult:
    ids, clock, events = SequentialIds(), FixedClock(), RecordingEventSink()
    media = InMemoryMediaStore()
    analyses = InMemoryRepository[Analysis]()
    betas = InMemoryRepository[BetaRecord]()
    videos = InMemoryRepository[VideoRecord]()
    marks = PillowMarkRenderer()

    analysis = AnalyzeBoulder(
        preprocessor=PillowPreprocessor(),
        detector=ColorHoldDetector(),
        raw_sink=InMemoryRawImageSink(),
        media=media,
        analyses=analyses,
        events=events,
        ids=ids,
        clock=clock,
    ).execute(case.image, device_id="eval")
    analysis = analysis.model_copy(update={"px_per_cm": case.px_per_cm})  # use the true scale
    analyses.save(analysis)
    detection = detection_scores(case.truth_holds, analysis.holds)

    mapping = {
        t.id: f.id for t, f in match_holds(case.truth_holds, analysis.holds, MATCH_DISTANCE_PX)
    }
    starts = [mapping[i] for i in case.truth.start_hold_ids if i in mapping]
    top = mapping.get(case.truth.top_hold_id)
    base = {
        "case_id": case.case_id,
        "detection_precision": detection.precision,
        "detection_recall": detection.recall,
        "color_accuracy": detection.color_accuracy,
    }
    if not starts or top is None:
        return CaseResult(
            **base,
            problem_mapped=False,
            beta_status="skipped",
            beta_attempts=0,
            n_moves=0,
            spec_valid=False,
            beta_latency_s=None,
            video_latency_s=None,
            error="start or top hold not detected",
        )

    SelectProblem(analyses=analyses, events=events, clock=clock).execute(
        analysis.id, start_hold_ids=starts, top_hold_id=top, color=case.truth.problem_color
    )
    record = RequestBeta(analyses=analyses, betas=betas, ids=ids, clock=clock).execute(
        analysis.id, profile
    )
    started = time.perf_counter()
    beta = ProduceBeta(
        analyses=analyses,
        betas=betas,
        media=media,
        marks=marks,
        planner=planner,
        validator=BetaValidator(),
        events=events,
        clock=clock,
    ).execute(record.id)
    beta_latency = time.perf_counter() - started

    spec_valid, video_latency, error = False, None, beta.error
    if beta.status is JobStatus.READY:
        video = RequestVideo(betas=betas, videos=videos, ids=ids, clock=clock).execute(beta.id)
        started = time.perf_counter()
        done = ProduceVideo(
            videos=videos,
            betas=betas,
            analyses=analyses,
            media=media,
            director=director,
            validator=MotionSpecValidator(),
            renderer=None,
            events=events,
            clock=clock,
            marks=marks,
        ).execute(video.id)
        video_latency = time.perf_counter() - started
        spec_valid = done.status is VideoStatus.DIRECTED
        error = error or done.error

    return CaseResult(
        **base,
        problem_mapped=True,
        beta_status=beta.status.value,
        beta_attempts=beta.attempts,
        n_moves=len(beta.plan.moves) if beta.plan else 0,
        spec_valid=spec_valid,
        beta_latency_s=round(beta_latency, 4),
        video_latency_s=round(video_latency, 4) if video_latency is not None else None,
        error=error,
    )
