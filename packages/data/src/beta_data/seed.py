"""Seed bronze with synthetic walls run through the real pipeline (offline adapters).

Each wall goes through AnalyzeBoulder → SelectProblem → beta → video exactly like production, so
bronze holds realistic events. Ground truth (true holds, problem) is stored beside it for evals,
and a little deterministic simulated feedback gives the gold marts something to aggregate.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from beta_core.domain.climber import ClimberProfile, ClimbingStyle
from beta_core.domain.records import (
    Analysis,
    BetaRecord,
    Feedback,
    FeedbackKind,
    JobStatus,
    VideoRecord,
)
from beta_core.services.analyze import AnalyzeBoulder
from beta_core.services.feedback import RecordFeedback
from beta_core.services.generate_beta import ProduceBeta, RequestBeta
from beta_core.services.generate_video import ProduceVideo, RequestVideo
from beta_core.services.select_problem import SelectProblem
from beta_core.testing import InMemoryMediaStore, InMemoryRepository
from beta_core.validation import BetaValidator, MotionSpecValidator
from beta_data.bronze import BronzeWriter
from beta_data.layout import Lakehouse
from beta_llm.heuristic import ChoreographyDirector, HeuristicBetaPlanner
from beta_vision.detect import ColorHoldDetector, match_holds
from beta_vision.overlay import PillowMarkRenderer
from beta_vision.preprocess import PillowPreprocessor
from beta_vision.synthetic import SyntheticWallGenerator

SEED_EPOCH = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
PROFILES = (
    ClimberProfile(height_cm=175, ape_index_cm=2, style=ClimbingStyle.BALANCED),
    ClimberProfile(height_cm=160, ape_index_cm=-1, style=ClimbingStyle.STATIC),
    ClimberProfile(height_cm=188, ape_index_cm=5, style=ClimbingStyle.DYNAMIC),
)
NOTE = "synthetic seed"


class _SeedClock:
    """Deterministic time: one second per call, starting at the seed's own minute."""

    def __init__(self, seed: int) -> None:
        self._now = SEED_EPOCH + timedelta(minutes=seed)

    def now(self) -> datetime:
        self._now += timedelta(seconds=1)
        return self._now


class _SeedIds:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._n = 0

    def new(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}_seed{self.seed:04d}_{self._n:03d}"


def seed(lake: Lakehouse, count: int, start: int = 0) -> list[str]:
    """Generate ``count`` synthetic walls (seeds ``start..start+count-1``); return analysis IDs."""
    writer = BronzeWriter(lake)
    preprocessor = PillowPreprocessor()
    detector = ColorHoldDetector()
    marks = PillowMarkRenderer()
    analysis_ids: list[str] = []
    for n in range(start, start + count):
        analysis_ids.append(_seed_one(n, writer, preprocessor, detector, marks))
    return analysis_ids


def _seed_one(
    n: int,
    writer: BronzeWriter,
    preprocessor: PillowPreprocessor,
    detector: ColorHoldDetector,
    marks: PillowMarkRenderer,
) -> str:
    wall = SyntheticWallGenerator(n).generate()
    clock, ids = _SeedClock(n), _SeedIds(n)
    media = InMemoryMediaStore()
    analyses = InMemoryRepository[Analysis]()
    betas = InMemoryRepository[BetaRecord]()
    videos = InMemoryRepository[VideoRecord]()
    feedback = InMemoryRepository[Feedback]()

    analysis = AnalyzeBoulder(
        preprocessor=preprocessor,
        detector=detector,
        raw_sink=writer,
        media=media,
        analyses=analyses,
        events=writer,
        ids=ids,
        clock=clock,
    ).execute(
        wall.image, device_id=f"dev_seed_{n:04d}", wall_height_cm=wall.height / wall.px_per_cm
    )

    writer.store_ground_truth(
        hashlib.sha256(wall.image).hexdigest(),
        {
            "seed": n,
            "width": wall.width,
            "height": wall.height,
            "px_per_cm": wall.px_per_cm,
            "problem_color": wall.problem_color,
            "start_hold_ids": list(wall.start_hold_ids),
            "top_hold_id": wall.top_hold_id,
            "foot_hold_ids": list(wall.foot_hold_ids),
            "holds": [h.model_dump(mode="json") for h in wall.holds],
        },
    )

    truth_to_detected = {t.id: f.id for t, f in match_holds(wall.holds, analysis.holds, 15.0)}
    starts = [truth_to_detected[i] for i in wall.start_hold_ids if i in truth_to_detected]
    top = truth_to_detected.get(wall.top_hold_id)
    if not starts or top is None:
        return analysis.id
    SelectProblem(analyses=analyses, events=writer, clock=clock).execute(
        analysis.id, start_hold_ids=starts, top_hold_id=top, color=wall.problem_color
    )

    record = RequestBeta(analyses=analyses, betas=betas, ids=ids, clock=clock).execute(
        analysis.id, PROFILES[n % len(PROFILES)]
    )
    beta = ProduceBeta(
        analyses=analyses,
        betas=betas,
        media=media,
        marks=marks,
        planner=HeuristicBetaPlanner(),
        validator=BetaValidator(),
        events=writer,
        clock=clock,
    ).execute(record.id)
    if beta.status is not JobStatus.READY or beta.plan is None:
        return analysis.id

    video = RequestVideo(betas=betas, videos=videos, ids=ids, clock=clock).execute(beta.id)
    ProduceVideo(
        videos=videos,
        betas=betas,
        analyses=analyses,
        media=media,
        director=ChoreographyDirector(),
        validator=MotionSpecValidator(),
        renderer=None,
        events=writer,
        clock=clock,
    ).execute(video.id)

    record_feedback = RecordFeedback(
        betas=betas, feedback=feedback, events=writer, ids=ids, clock=clock
    )
    crux = beta.plan.crux_move_indices[0] if beta.plan.crux_move_indices else 0
    match n % 3:
        case 0:
            record_feedback.execute(beta.id, FeedbackKind.SENT, note=NOTE)
            record_feedback.execute(beta.id, FeedbackKind.USEFUL, note=NOTE)
        case 1:
            record_feedback.execute(beta.id, FeedbackKind.REWATCH, move_index=crux, note=NOTE)
            record_feedback.execute(beta.id, FeedbackKind.REWATCH, move_index=crux, note=NOTE)
            record_feedback.execute(
                beta.id, FeedbackKind.MOVE_LOOKS_WRONG, move_index=crux, note=NOTE
            )
        case _:
            record_feedback.execute(beta.id, FeedbackKind.NOT_USEFUL, note=NOTE)
            record_feedback.execute(beta.id, FeedbackKind.REWATCH, move_index=0, note=NOTE)
    return analysis.id
