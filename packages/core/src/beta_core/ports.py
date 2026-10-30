"""Ports: the interfaces the domain needs from the outside world (ADR-0002).

Adapters live in other packages: ``beta_vision`` (images, detection, overlays), ``beta_llm``
(planner, director, classifier), ``beta_data`` (bronze sinks), ``beta_api`` (repositories, media,
renderer client). In-memory fakes for tests live in :mod:`beta_core.testing`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, TypeVar

from pydantic import Field

from beta_core.domain.base import DomainModel
from beta_core.domain.beta import BetaPlan
from beta_core.domain.climber import BodyModel, ClimberProfile
from beta_core.domain.events import DomainEvent
from beta_core.domain.holds import Hold, Problem
from beta_core.domain.motion import ImageRef, MotionSpec
from beta_core.domain.violations import Violation

# ---------------------------------------------------------------- infrastructure


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self, prefix: str) -> str: ...


class HasId(Protocol):
    @property
    def id(self) -> str: ...


T = TypeVar("T", bound=HasId)


class Repository(Protocol[T]):
    def get(self, entity_id: str) -> T:
        """Return the entity or raise ``NotFoundError``."""
        ...

    def save(self, entity: T) -> None:
        """Insert or replace."""
        ...

    def find(self, **where: object) -> list[T]:
        """Entities whose attributes equal every ``where`` value, oldest first."""
        ...


class MediaStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


class EventSink(Protocol):
    def emit(self, event: DomainEvent) -> None: ...


# ---------------------------------------------------------------- images


class SanitizedUpload(DomainModel):
    """Upload bytes with GPS removed (ADR-0007); otherwise as received."""

    data: bytes
    sha256: str
    content_type: str
    gps_stripped: bool


class NormalizedImage(DomainModel):
    """Oriented, resized, EXIF-free JPEG. All hold coordinates live in this image's pixel space."""

    data: bytes
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    sha256: str
    dhash: str
    content_type: str = "image/jpeg"


class RawImageSink(Protocol):
    def store_raw(self, upload: SanitizedUpload) -> str:
        """Persist the sanitized upload in bronze; return its key."""
        ...


class ImagePreprocessor(Protocol):
    def sanitize(self, raw: bytes) -> SanitizedUpload: ...

    def normalize(self, data: bytes) -> NormalizedImage: ...


class HoldDetector(Protocol):
    version: str

    def detect(self, image: NormalizedImage) -> list[Hold]: ...


class HoldClassifier(Protocol):
    def classify(self, image: NormalizedImage, holds: Sequence[Hold]) -> list[Hold]: ...


class MarkRenderer(Protocol):
    def render_marks(self, image: NormalizedImage, holds: Sequence[Hold]) -> NormalizedImage:
        """Draw numbered markers on ``holds`` (set-of-marks prompting)."""
        ...


# ---------------------------------------------------------------- generation


class BetaRequest(DomainModel):
    plan_id: str
    analysis_id: str
    problem: Problem
    image: NormalizedImage
    profile: ClimberProfile
    body: BodyModel
    px_per_cm: float
    previous_attempt: BetaPlan | None = None
    previous_violations: tuple[Violation, ...] = ()


class BetaPlanner(Protocol):
    name: str

    def plan(self, request: BetaRequest) -> BetaPlan: ...


class MotionRequest(DomainModel):
    beta: BetaPlan
    problem: Problem
    image: NormalizedImage
    image_ref: ImageRef
    body: BodyModel
    px_per_cm: float
    previous_spec: MotionSpec | None = None
    previous_violations: tuple[Violation, ...] = ()


class MotionDirector(Protocol):
    name: str

    def direct(self, request: MotionRequest) -> MotionSpec: ...


class RenderResult(DomainModel):
    video_key: str
    poster_key: str
    duration_s: float


class VideoRenderer(Protocol):
    def render(self, spec: MotionSpec, video_id: str) -> RenderResult: ...
