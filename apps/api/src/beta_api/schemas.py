"""HTTP wire models (v1). Stable on purpose; domain models can evolve behind them.

BetaKit (apps/ios) mirrors these shapes; examples live in contracts/api/examples.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from beta_core.domain.beta import BetaPlan
from beta_core.domain.climber import ClimberProfile, ClimbingStyle
from beta_core.domain.grades import Grade
from beta_core.domain.holds import Hold, Problem
from beta_core.domain.records import Analysis, BetaRecord, Feedback, FeedbackKind, VideoRecord


class HoldOut(BaseModel):
    id: int
    x: float
    y: float
    w: float
    h: float
    cx: float
    cy: float
    color: str
    type: str
    confidence: float

    @classmethod
    def of(cls, h: Hold) -> HoldOut:
        b = h.bbox
        return cls(
            id=h.id,
            x=b.x,
            y=b.y,
            w=b.w,
            h=b.h,
            cx=h.center.x,
            cy=h.center.y,
            color=h.color,
            type=h.hold_type.value,
            confidence=h.confidence,
        )


class ProblemOut(BaseModel):
    color: str | None
    start_hold_ids: list[int]
    top_hold_id: int
    hold_ids: list[int]

    @classmethod
    def of(cls, p: Problem) -> ProblemOut:
        return cls(
            color=p.color,
            start_hold_ids=list(p.start_hold_ids),
            top_hold_id=p.top_hold_id,
            hold_ids=sorted(p.hold_ids),
        )


class AnalysisOut(BaseModel):
    id: str
    created_at: datetime
    image_url: str
    image_width: int
    image_height: int
    holds: list[HoldOut]
    color_groups: dict[str, list[int]]
    px_per_cm: float
    scale_method: str
    problem: ProblemOut | None


class ProblemIn(BaseModel):
    start_hold_ids: list[int] = Field(min_length=1, max_length=2)
    top_hold_id: int
    hold_ids: list[int] | None = None
    color: str | None = None


class ProfileIn(BaseModel):
    height_cm: float = Field(ge=120, le=230)
    ape_index_cm: float = Field(default=0, ge=-20, le=30)
    max_grade: str = "V3"
    style: ClimbingStyle = ClimbingStyle.BALANCED

    def to_domain(self) -> ClimberProfile:
        return ClimberProfile(
            height_cm=self.height_cm,
            ape_index_cm=self.ape_index_cm,
            max_grade=Grade.parse(self.max_grade),
            style=self.style,
        )


class BetaIn(BaseModel):
    profile: ProfileIn


class ContactsOut(BaseModel):
    lh: int | None
    rh: int | None
    lf: int | None
    rf: int | None


class MoveOut(BaseModel):
    index: int
    limb: str
    hold_id: int
    technique: str
    cue: str
    is_crux: bool


class ViolationOut(BaseModel):
    code: str
    message: str
    move_index: int | None


class BetaOut(BaseModel):
    id: str
    analysis_id: str
    status: str
    start: ContactsOut | None
    moves: list[MoveOut]
    summary: str
    grade: str | None
    grade_font: str | None
    confidence: float | None
    style: str | None
    planner: str | None
    attempts: int
    violations: list[ViolationOut]
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, r: BetaRecord) -> BetaOut:
        plan: BetaPlan | None = r.plan
        crux = set(plan.crux_move_indices) if plan else set()
        return cls(
            id=r.id,
            analysis_id=r.analysis_id,
            status=r.status.value,
            start=ContactsOut(**plan.start.model_dump()) if plan else None,
            moves=[
                MoveOut(
                    index=m.index,
                    limb=m.limb.value,
                    hold_id=m.hold_id,
                    technique=m.technique.value,
                    cue=m.cue,
                    is_crux=m.index in crux,
                )
                for m in (plan.moves if plan else ())
            ],
            summary=plan.summary if plan else "",
            grade=str(plan.grade_estimate) if plan and plan.grade_estimate else None,
            grade_font=plan.grade_estimate.font if plan and plan.grade_estimate else None,
            confidence=plan.confidence if plan else None,
            style=plan.style.value if plan else None,
            planner=plan.provenance.planner if plan else None,
            attempts=r.attempts,
            violations=[
                ViolationOut(code=v.code.value, message=v.message, move_index=v.move_index)
                for v in r.violations
            ],
            error=r.error,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


class ChapterOut(BaseModel):
    move_index: int
    title: str
    start_s: float


class VideoOut(BaseModel):
    id: str
    beta_id: str
    status: str
    video_url: str | None
    poster_url: str | None
    duration_s: float | None
    chapters: list[ChapterOut]
    error: str | None
    created_at: datetime
    updated_at: datetime


class FeedbackIn(BaseModel):
    kind: FeedbackKind
    move_index: int | None = None
    note: str = Field(default="", max_length=280)


class FeedbackOut(BaseModel):
    id: str
    kind: str
    move_index: int | None
    created_at: datetime

    @classmethod
    def of(cls, f: Feedback) -> FeedbackOut:
        return cls(id=f.id, kind=f.kind.value, move_index=f.move_index, created_at=f.created_at)


class HealthOut(BaseModel):
    status: str
    version: str
    planner: str
    director: str
    renderer: bool


def analysis_out(a: Analysis, image_url: str) -> AnalysisOut:
    return AnalysisOut(
        id=a.id,
        created_at=a.created_at,
        image_url=image_url,
        image_width=a.image.width,
        image_height=a.image.height,
        holds=[HoldOut.of(h) for h in a.holds],
        color_groups=a.color_groups(),
        px_per_cm=a.px_per_cm,
        scale_method=a.scale_method.value,
        problem=ProblemOut.of(a.problem) if a.problem else None,
    )


def video_out(v: VideoRecord, video_url: str | None, poster_url: str | None) -> VideoOut:
    chapters = []
    if v.spec is not None:
        fps = v.spec.meta.fps
        chapters = [
            ChapterOut(
                move_index=c.move_index, title=c.title, start_s=round(c.start_frame / fps, 3)
            )
            for c in v.spec.chapters
        ]
    return VideoOut(
        id=v.id,
        beta_id=v.beta_id,
        status=v.status.value,
        video_url=video_url,
        poster_url=poster_url,
        duration_s=v.duration_s,
        chapters=chapters,
        error=v.error,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )
