"""MotionSpec: the declarative timeline a route video is rendered from (ADR-0010).

Two layers:

* :class:`MotionDraft` — what the motion director (Claude or a heuristic) decides: pacing, easing,
  hip placement, camera, captions. Lenient, LLM-facing.
* :class:`MotionSpec` — the fully resolved, versioned timeline the renderer consumes. Built in code by
  :func:`beta_core.choreography.assemble_motion_spec`; limb contacts always come from the BetaPlan.

Coordinates are pixels in the normalised image. ``Camera.zoom == 1`` means the whole image is
visible inside the output frame; ``zoom == 2`` magnifies 2x around ``Camera.center``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from beta_core.domain.base import DomainModel, DraftModel
from beta_core.domain.beta import Contacts, Limb, Provenance, Technique
from beta_core.domain.climber import BodyModel
from beta_core.domain.geometry import Point
from beta_core.domain.holds import HoldRole

CAPTION_MAX = 60
CALLOUT_MAX = 40
CHAPTER_TITLE_MAX = 48
ZOOM_MIN = 1.0
ZOOM_MAX = 4.0
DURATION_MIN_S = 0.3
DURATION_MAX_S = 6.0


class Easing(StrEnum):
    LINEAR = "linear"
    EASE_IN_OUT = "ease_in_out"
    EASE_OUT = "ease_out"
    SNAP = "snap"  # fast launch, soft catch: dynamic moves


class Camera(DomainModel):
    center: Point
    zoom: float = Field(default=1.0, ge=ZOOM_MIN, le=ZOOM_MAX)


class HoldHighlight(DomainModel):
    kind: Literal["highlight"] = "highlight"
    hold_id: int
    color: str | None = None


class MoveArrow(DomainModel):
    kind: Literal["arrow"] = "arrow"
    limb: Limb
    from_hold_id: int | None = None
    to_hold_id: int


class Caption(DomainModel):
    kind: Literal["caption"] = "caption"
    text: str = Field(min_length=1, max_length=CAPTION_MAX)


class Callout(DomainModel):
    kind: Literal["callout"] = "callout"
    text: str = Field(min_length=1, max_length=CALLOUT_MAX)
    technique: Technique | None = None
    hold_id: int | None = None


class Trail(DomainModel):
    kind: Literal["trail"] = "trail"
    limb: Limb


Annotation = Annotated[
    HoldHighlight | MoveArrow | Caption | Callout | Trail, Field(discriminator="kind")
]


class SpecHold(DomainModel):
    id: int
    center: Point
    radius: float = Field(gt=0)
    color: str
    role: HoldRole


class Keyframe(DomainModel):
    """The pose reached at the end of this segment. ``move_index == -1`` is the start position."""

    move_index: int = Field(ge=-1)
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(ge=1)
    contacts: Contacts
    hip: Point
    limb: Limb | None = None
    technique: Technique | None = None
    easing: Easing = Easing.EASE_IN_OUT
    camera: Camera
    annotations: tuple[Annotation, ...] = ()
    slow_motion: bool = False

    @property
    def end_frame(self) -> int:
        return self.start_frame + self.duration_frames


class Chapter(DomainModel):
    move_index: int = Field(ge=0)
    start_frame: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=CHAPTER_TITLE_MAX)


class MotionMeta(DomainModel):
    fps: int = Field(default=30, ge=12, le=60)
    width: int = Field(default=1080, gt=0)
    height: int = Field(default=1920, gt=0)
    duration_frames: int = Field(ge=1)


class ImageRef(DomainModel):
    uri: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class MotionSpec(DomainModel):
    version: Literal["1"] = "1"
    beta_id: str
    meta: MotionMeta
    image: ImageRef
    px_per_cm: float = Field(gt=0)
    body: BodyModel
    holds: tuple[SpecHold, ...]
    keyframes: tuple[Keyframe, ...] = Field(min_length=1)
    chapters: tuple[Chapter, ...]
    provenance: Provenance


def _truncate(value: object, limit: int) -> object:
    return value[:limit].strip() or None if isinstance(value, str) else value


class MoveDirection(DraftModel):
    """Director's choices for one segment. ``move_index == -1`` directs the opening start pose."""

    move_index: int = Field(ge=-1)
    duration_s: float = Field(
        default=1.2,
        description=f"Seconds this move takes on screen ({DURATION_MIN_S}-{DURATION_MAX_S}).",
    )
    easing: Easing = Easing.EASE_IN_OUT
    hip: Point | None = Field(
        default=None, description="Hip position in image pixels; omit to auto-place."
    )
    camera: Camera | None = Field(
        default=None, description="Framing; omit to auto-frame the active limbs."
    )
    caption: str | None = Field(
        default=None, description=f"On-screen caption, <= {CAPTION_MAX} chars."
    )
    callout: str | None = Field(
        default=None, description=f"Short label near the hold, <= {CALLOUT_MAX} chars."
    )
    slow_motion: bool = False
    show_trail: bool = False

    @field_validator("duration_s", mode="before")
    @classmethod
    def _clamp_duration(cls, value: object) -> object:
        if isinstance(value, int | float):
            return min(max(float(value), DURATION_MIN_S), DURATION_MAX_S)
        return value

    @field_validator("camera", mode="before")
    @classmethod
    def _clamp_zoom(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("zoom"), int | float):
            return {**value, "zoom": min(max(float(value["zoom"]), ZOOM_MIN), ZOOM_MAX)}
        return value

    @field_validator("caption", mode="before")
    @classmethod
    def _cap_caption(cls, value: object) -> object:
        return _truncate(value, CAPTION_MAX)

    @field_validator("callout", mode="before")
    @classmethod
    def _cap_callout(cls, value: object) -> object:
        return _truncate(value, CALLOUT_MAX)


class MotionDraft(DraftModel):
    directions: list[MoveDirection] = Field(
        default_factory=list,
        description="One entry per segment you want to direct; others use defaults.",
    )
