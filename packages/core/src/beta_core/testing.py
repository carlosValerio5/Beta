"""In-memory fakes and canonical fixtures, shared by every package's tests and by contract export.

The *ladder* fixture is a hand-placed yellow problem on a 1000x1500 px image at 3 px/cm (a 5 m tall
frame) with a 12-move beta that a 175 cm climber can reach. It is the source of the cross-language
example MotionSpec.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from beta_core.choreography import assemble_motion_spec
from beta_core.domain.beta import BetaPlan, Contacts, Limb, Move, Provenance, Technique
from beta_core.domain.climber import ClimberProfile, ClimbingStyle
from beta_core.domain.events import DomainEvent, EventName
from beta_core.domain.geometry import BBox
from beta_core.domain.grades import Grade
from beta_core.domain.holds import Hold, HoldType, Problem
from beta_core.domain.motion import ImageRef, MotionDraft, MotionSpec
from beta_core.domain.records import Analysis, BetaRecord, JobStatus, StoredImage
from beta_core.errors import NotFoundError
from beta_core.ports import (
    HasId,
    MotionRequest,
    NormalizedImage,
    RenderResult,
    SanitizedUpload,
)
from beta_core.scale import ScaleMethod

# ---------------------------------------------------------------- fixtures

LADDER_PX_PER_CM = 3.0
LADDER_IMAGE = ImageRef(uri="images/ladder.jpg", width=1000, height=1500)
FIXED_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)

#: (id, x, y, colour, type) — centres in pixels.
_LADDER_HOLDS: tuple[tuple[int, float, float, str, HoldType], ...] = (
    (0, 450, 1050, "yellow", HoldType.JUG),
    (1, 560, 1050, "yellow", HoldType.JUG),
    (2, 430, 1350, "yellow", HoldType.FOOTHOLD),
    (3, 580, 1350, "yellow", HoldType.FOOTHOLD),
    (4, 420, 930, "yellow", HoldType.JUG),
    (5, 590, 810, "yellow", HoldType.CRIMP),
    (6, 430, 690, "yellow", HoldType.SLOPER),
    (7, 580, 570, "yellow", HoldType.CRIMP),
    (8, 500, 450, "yellow", HoldType.JUG),
    (9, 440, 1200, "yellow", HoldType.FOOTHOLD),
    (10, 570, 1200, "yellow", HoldType.FOOTHOLD),
    (11, 250, 900, "blue", HoldType.JUG),
    (12, 760, 700, "blue", HoldType.PINCH),
    (13, 300, 500, "red", HoldType.EDGE),
)
_HOLD_PX = 40.0


def ladder_holds() -> tuple[Hold, ...]:
    return tuple(
        Hold(
            id=i,
            bbox=BBox(x=x - _HOLD_PX / 2, y=y - _HOLD_PX / 2, w=_HOLD_PX, h=_HOLD_PX),
            color=color,
            hold_type=kind,
        )
        for i, x, y, color, kind in _LADDER_HOLDS
    )


def ladder_problem() -> Problem:
    return Problem(
        holds=tuple(h for h in ladder_holds() if h.color == "yellow"),
        start_hold_ids=(0, 1),
        top_hold_id=8,
        color="yellow",
    )


def ladder_plan() -> BetaPlan:
    steps: list[tuple[Limb, int, Technique, str]] = [
        (Limb.LH, 4, Technique.REACH, "Reach up left to the jug"),
        (Limb.LF, 9, Technique.STEP, "Left foot up"),
        (Limb.RF, 10, Technique.STEP, "Right foot up"),
        (Limb.RH, 5, Technique.GASTON, "Thumb-down gaston, push out right"),
        (Limb.LF, 0, Technique.HIGH_STEP, "High step onto the start jug"),
        (Limb.LH, 6, Technique.REACH, "Stand up and slap the sloper"),
        (Limb.RF, 1, Technique.STEP, "Right foot to the other start jug"),
        (Limb.RH, 7, Technique.LOCK_OFF, "Lock off low and reach the crimp"),
        (Limb.LF, 4, Technique.HIGH_STEP, "Rock over onto the first jug"),
        (Limb.RF, 5, Technique.STEP, "Right foot to the gaston"),
        (Limb.LH, 8, Technique.REACH, "Top out jug, left hand"),
        (Limb.RH, 8, Technique.MATCH, "Match the top"),
    ]
    return BetaPlan(
        id="bet_ladder",
        analysis_id="ana_ladder",
        start=Contacts(lh=0, rh=1, lf=2, rf=3),
        moves=tuple(
            Move(index=i, limb=limb, hold_id=hold, technique=tech, cue=cue)
            for i, (limb, hold, tech, cue) in enumerate(steps)
        ),
        crux_move_indices=(7,),
        summary="Climb the ladder of yellows, keeping feet high so the crimp at move 8 is a short lock-off.",
        grade_estimate=Grade(v=3),
        confidence=0.8,
        style=ClimbingStyle.STATIC,
        provenance=Provenance(planner="fixture@1"),
    )


def profile_175() -> ClimberProfile:
    return ClimberProfile(
        height_cm=175, ape_index_cm=0, max_grade=Grade(v=4), style=ClimbingStyle.BALANCED
    )


def ladder_analysis(media: InMemoryMediaStore) -> Analysis:
    media.put(LADDER_IMAGE.uri, b"ladder-jpeg", "image/jpeg")
    return Analysis(
        id="ana_ladder",
        device_id="dev_test",
        created_at=FIXED_NOW,
        image=StoredImage(
            key=LADDER_IMAGE.uri,
            width=LADDER_IMAGE.width,
            height=LADDER_IMAGE.height,
            sha256="0" * 64,
            dhash="0" * 16,
        ),
        holds=ladder_holds(),
        detector="fixture@1",
        px_per_cm=LADDER_PX_PER_CM,
        scale_method=ScaleMethod.WALL_HEIGHT,
        problem=ladder_problem(),
    )


def ladder_beta_record(analysis: Analysis) -> BetaRecord:
    return BetaRecord(
        id="bet_ladder",
        analysis_id=analysis.id,
        profile=profile_175(),
        status=JobStatus.READY,
        plan=ladder_plan().model_copy(update={"analysis_id": analysis.id}),
        attempts=1,
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


# ---------------------------------------------------------------- infrastructure fakes


class FixedClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SequentialIds:
    def __init__(self) -> None:
        self._n = 0

    def new(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}_{self._n:06d}"


class InMemoryRepository[T: HasId]:
    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def get(self, entity_id: str) -> T:
        try:
            return self._items[entity_id]
        except KeyError:
            raise NotFoundError("entity", entity_id) from None

    def save(self, entity: T) -> None:
        self._items[entity.id] = entity

    def find(self, **where: object) -> list[T]:
        return [
            e for e in self._items.values() if all(getattr(e, k) == v for k, v in where.items())
        ]


class InMemoryMediaStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def get(self, key: str) -> bytes:
        try:
            return self.objects[key][0]
        except KeyError:
            raise NotFoundError("media", key) from None

    def exists(self, key: str) -> bool:
        return key in self.objects


class InMemoryRawImageSink:
    def __init__(self) -> None:
        self.stored: list[SanitizedUpload] = []

    def store_raw(self, upload: SanitizedUpload) -> str:
        self.stored.append(upload)
        return f"bronze/images/{upload.sha256}"


class RecordingEventSink:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def emit(self, event: DomainEvent) -> None:
        self.events.append(event)

    def names(self) -> list[EventName]:
        return [e.name for e in self.events]


# ---------------------------------------------------------------- adapter fakes


class FakePreprocessor:
    def __init__(self, gps: bool = False, width: int = 1000, height: int = 1500) -> None:
        self.gps = gps
        self.width = width
        self.height = height

    def sanitize(self, raw: bytes) -> SanitizedUpload:
        return SanitizedUpload(
            data=raw,
            sha256=hashlib.sha256(raw).hexdigest(),
            content_type="image/jpeg",
            gps_stripped=self.gps,
        )

    def normalize(self, data: bytes) -> NormalizedImage:
        out = b"norm:" + data
        return NormalizedImage(
            data=out,
            width=self.width,
            height=self.height,
            sha256=hashlib.sha256(out).hexdigest(),
            dhash="0" * 16,
        )


class FakeDetector:
    version = "fake-detector@1"

    def __init__(self, holds: Sequence[Hold]) -> None:
        self.holds = list(holds)

    def detect(self, image: NormalizedImage) -> list[Hold]:
        return list(self.holds)


class FakeMarkRenderer:
    def render_marks(self, image: NormalizedImage, holds: Sequence[Hold]) -> NormalizedImage:
        return image.model_copy(update={"data": b"marked:" + image.data})


class DraftMotionDirector:
    """Assembles a fixed draft — the simplest valid director."""

    name = "draft-director@1"

    def __init__(self, draft: MotionDraft) -> None:
        self.draft = draft

    def direct(self, request: MotionRequest) -> MotionSpec:
        return assemble_motion_spec(
            self.draft,
            plan=request.beta,
            problem=request.problem,
            image=request.image_ref,
            body_cm=request.body,
            px_per_cm=request.px_per_cm,
            provenance=Provenance(planner=self.name),
        )


class FakeRenderer:
    def __init__(self) -> None:
        self.rendered: list[str] = []

    def render(self, spec: MotionSpec, video_id: str) -> RenderResult:
        self.rendered.append(video_id)
        return RenderResult(
            video_key=f"videos/{video_id}.mp4",
            poster_key=f"videos/{video_id}.jpg",
            duration_s=spec.meta.duration_frames / spec.meta.fps,
        )


#: A tiny stand-in for a marked JPEG, sized like the ladder image (adapters never decode it).
FAKE_IMAGE = NormalizedImage(
    data=b"\xff\xd8fake-jpeg",
    width=LADDER_IMAGE.width,
    height=LADDER_IMAGE.height,
    sha256="a" * 64,
    dhash="0" * 16,
)
