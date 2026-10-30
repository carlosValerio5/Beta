"""A beta: the ordered moves that climb a problem."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator

from beta_core.domain.base import DomainModel, DraftModel
from beta_core.domain.climber import ClimbingStyle
from beta_core.domain.grades import Grade

CUE_MAX = 160
SUMMARY_MAX = 600


class Limb(StrEnum):
    LH = "lh"
    RH = "rh"
    LF = "lf"
    RF = "rf"

    @property
    def is_hand(self) -> bool:
        return self in (Limb.LH, Limb.RH)

    @property
    def label(self) -> str:
        return {"lh": "Left hand", "rh": "Right hand", "lf": "Left foot", "rf": "Right foot"}[
            self.value
        ]

    @classmethod
    def hands(cls) -> tuple[Limb, Limb]:
        return (cls.LH, cls.RH)

    @classmethod
    def feet(cls) -> tuple[Limb, Limb]:
        return (cls.LF, cls.RF)


class Technique(StrEnum):
    REACH = "reach"
    CROSS = "cross"
    MATCH = "match"
    GASTON = "gaston"
    UNDERCLING = "undercling"
    SIDEPULL = "sidepull"
    LOCK_OFF = "lock_off"
    DEADPOINT = "deadpoint"
    DYNO = "dyno"
    MANTLE = "mantle"
    FLAG = "flag"
    DROP_KNEE = "drop_knee"
    HEEL_HOOK = "heel_hook"
    TOE_HOOK = "toe_hook"
    HIGH_STEP = "high_step"
    SMEAR = "smear"
    ROCKOVER = "rockover"
    BUMP = "bump"
    STEP = "step"

    @property
    def is_dynamic(self) -> bool:
        return self in (Technique.DEADPOINT, Technique.DYNO)

    @property
    def is_notable(self) -> bool:
        """Worth a callout in the video (anything beyond a plain reach or step)."""
        return self not in (Technique.REACH, Technique.STEP)

    @property
    def label(self) -> str:
        return self.value.replace("_", " ")


class Contacts(DomainModel):
    """Which hold each limb is on. ``None`` means the limb is free (smearing, flagging, cutting)."""

    lh: int | None = None
    rh: int | None = None
    lf: int | None = None
    rf: int | None = None

    def get(self, limb: Limb) -> int | None:
        value: int | None = getattr(self, limb.value)
        return value

    def with_contact(self, limb: Limb, hold_id: int | None) -> Contacts:
        return self.model_copy(update={limb.value: hold_id})

    def items(self) -> list[tuple[Limb, int | None]]:
        return [(limb, self.get(limb)) for limb in Limb]


class Move(DomainModel):
    index: int = Field(ge=0)
    limb: Limb
    hold_id: int = Field(ge=0)
    technique: Technique = Technique.REACH
    cue: str = Field(default="", max_length=CUE_MAX)


class Provenance(DomainModel):
    """Who produced an artifact: planner/director name@version, prompt version, model, detector."""

    planner: str
    prompt: str | None = None
    model: str | None = None
    detector: str | None = None


class BetaPlan(DomainModel):
    id: str
    analysis_id: str
    start: Contacts
    moves: tuple[Move, ...]
    crux_move_indices: tuple[int, ...] = ()
    summary: str = Field(default="", max_length=SUMMARY_MAX)
    grade_estimate: Grade | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    style: ClimbingStyle = ClimbingStyle.BALANCED
    provenance: Provenance

    def states(self) -> list[Contacts]:
        """Contacts before the first move, then after each move (``len(moves) + 1`` entries)."""
        states = [self.start]
        for move in self.moves:
            states.append(states[-1].with_contact(move.limb, move.hold_id))
        return states

    @property
    def final_contacts(self) -> Contacts:
        return self.states()[-1]


def _truncate(value: object, limit: int) -> object:
    return value[:limit] if isinstance(value, str) else value


class MoveDraft(DraftModel):
    limb: Limb
    hold_id: int = Field(ge=0, description="ID of the numbered hold this limb moves to.")
    technique: Technique = Technique.REACH
    cue: str = Field(default="", description="One short coaching cue (max ~12 words).")

    @field_validator("cue", mode="before")
    @classmethod
    def _cap_cue(cls, value: object) -> object:
        return _truncate(value, CUE_MAX)


class BetaDraft(DraftModel):
    """What the beta planner returns. IDs and provenance are added in code by :meth:`to_plan`."""

    start: Contacts = Field(description="Starting hold for each limb; feet may be null.")
    moves: list[MoveDraft] = Field(default_factory=list, description="One limb movement per entry.")
    crux_move_indices: list[int] = Field(
        default_factory=list, description="0-based indices of the hardest moves."
    )
    summary: str = Field(default="", description="Two sentences on the overall strategy.")
    grade_estimate: str | None = Field(
        default=None, description="V-scale or Font grade, e.g. 'V4'."
    )
    confidence: float = Field(default=0.5, ge=0, le=1)
    style: ClimbingStyle = ClimbingStyle.BALANCED

    @field_validator("summary", mode="before")
    @classmethod
    def _cap_summary(cls, value: object) -> object:
        return _truncate(value, SUMMARY_MAX)

    def to_plan(self, *, plan_id: str, analysis_id: str, provenance: Provenance) -> BetaPlan:
        grade: Grade | None
        try:
            grade = Grade.parse(self.grade_estimate) if self.grade_estimate else None
        except ValueError:
            grade = None
        return BetaPlan(
            id=plan_id,
            analysis_id=analysis_id,
            start=self.start,
            moves=tuple(
                Move(index=i, limb=m.limb, hold_id=m.hold_id, technique=m.technique, cue=m.cue)
                for i, m in enumerate(self.moves)
            ),
            crux_move_indices=tuple(self.crux_move_indices),
            summary=self.summary,
            grade_estimate=grade,
            confidence=self.confidence,
            style=self.style,
            provenance=provenance,
        )
