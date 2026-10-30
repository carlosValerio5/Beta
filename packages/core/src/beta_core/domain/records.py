"""Aggregates with a lifecycle, persisted by repositories."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from beta_core.domain.base import DomainModel
from beta_core.domain.beta import BetaPlan
from beta_core.domain.climber import ClimberProfile
from beta_core.domain.holds import Hold, Problem
from beta_core.domain.motion import MotionSpec
from beta_core.domain.violations import Violation
from beta_core.errors import UnknownHoldError
from beta_core.scale import ScaleMethod


class StoredImage(DomainModel):
    key: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    sha256: str
    dhash: str


class Analysis(DomainModel):
    id: str
    device_id: str
    created_at: datetime
    image: StoredImage
    holds: tuple[Hold, ...]
    detector: str
    px_per_cm: float = Field(gt=0)
    scale_method: ScaleMethod
    problem: Problem | None = None

    def hold(self, hold_id: int) -> Hold:
        for h in self.holds:
            if h.id == hold_id:
                return h
        raise UnknownHoldError(hold_id)

    def color_groups(self) -> dict[str, list[int]]:
        groups: dict[str, list[int]] = defaultdict(list)
        for h in self.holds:
            groups[h.color].append(h.id)
        return {color: sorted(ids) for color, ids in sorted(groups.items())}


class JobStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class BetaRecord(DomainModel):
    id: str
    analysis_id: str
    profile: ClimberProfile
    status: JobStatus
    plan: BetaPlan | None = None
    violations: tuple[Violation, ...] = ()
    attempts: int = 0
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoStatus(StrEnum):
    DIRECTING = "directing"
    DIRECTED = "directed"  # spec ready, no renderer configured
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (VideoStatus.DIRECTED, VideoStatus.READY, VideoStatus.FAILED)


class VideoRecord(DomainModel):
    id: str
    beta_id: str
    status: VideoStatus
    spec: MotionSpec | None = None
    video_key: str | None = None
    poster_key: str | None = None
    duration_s: float | None = None
    violations: tuple[Violation, ...] = ()
    attempts: int = 0
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class FeedbackKind(StrEnum):
    SENT = "sent"
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    MOVE_LOOKS_WRONG = "move_looks_wrong"
    REWATCH = "rewatch"
    WATCHED_TO_END = "watched_to_end"

    @property
    def requires_move(self) -> bool:
        return self in (FeedbackKind.MOVE_LOOKS_WRONG, FeedbackKind.REWATCH)

    @property
    def is_playback(self) -> bool:
        return self in (FeedbackKind.REWATCH, FeedbackKind.WATCHED_TO_END)


class Feedback(DomainModel):
    id: str
    beta_id: str
    kind: FeedbackKind
    move_index: int | None = None
    note: str = Field(default="", max_length=280)
    created_at: datetime
