"""Versioned table contracts for the silver and gold layers (docs/data/contracts.md).

A contract is a Pydantic row model plus a version. The Arrow schema is derived from the row model
so Parquet files and validation can never disagree. Changing columns = bump the version.
"""

from __future__ import annotations

import types
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Union, get_args, get_origin

import pyarrow as pa
from pydantic import BaseModel, ConfigDict

Layer = Literal["silver", "gold"]


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- silver


class SilverImage(Row):
    image_sha256: str
    source_sha256: str
    analysis_id: str
    device_id: str
    width: int
    height: int
    dhash: str
    gps_stripped: bool
    duplicate_of: str | None
    ingested_at: datetime


class SilverHold(Row):
    analysis_id: str
    hold_id: int
    x: float
    y: float
    w: float
    h: float
    color: str
    hold_type: str
    confidence: float
    detector: str


class SilverProblem(Row):
    analysis_id: str
    color: str | None
    start_hold_ids: list[int]
    top_hold_id: int
    hold_ids: list[int]
    selected_at: datetime


class SilverBeta(Row):
    beta_id: str
    analysis_id: str
    status: str
    planner: str | None
    prompt: str | None
    model: str | None
    n_moves: int
    grade_v: int | None
    confidence: float | None
    style: str | None
    attempts: int
    height_cm: float | None
    ape_index_cm: float | None
    error: str | None
    created_at: datetime


class SilverMove(Row):
    beta_id: str
    move_index: int
    limb: str
    hold_id: int
    technique: str
    cue: str
    is_crux: bool


class SilverMotionSpec(Row):
    video_id: str
    beta_id: str
    director: str
    prompt: str | None
    model: str | None
    fps: int
    duration_frames: int
    n_keyframes: int
    n_captions: int
    n_slow_motion: int
    attempts: int
    directed_at: datetime


class SilverKeyframe(Row):
    video_id: str
    move_index: int
    start_frame: int
    duration_frames: int
    hip_x: float
    hip_y: float
    camera_x: float
    camera_y: float
    zoom: float
    easing: str
    slow_motion: bool
    n_annotations: int


class SilverFeedback(Row):
    feedback_id: str
    beta_id: str
    kind: str
    move_index: int | None
    note: str
    created_at: datetime


class SilverRender(Row):
    video_id: str
    beta_id: str
    status: str
    duration_s: float | None
    error: str | None
    at: datetime


# ---------------------------------------------------------------- gold


class GoldBetaQuality(Row):
    planner: str
    n_betas: int
    n_sent: int
    n_useful: int
    n_not_useful: int
    n_looks_wrong: int
    useful_rate: float


class GoldConfusingMove(Row):
    beta_id: str
    move_index: int
    technique: str
    limb: str
    rewatches: int
    looks_wrong: int
    score: int


# ---------------------------------------------------------------- registry

_SCALARS: dict[Any, pa.DataType] = {
    str: pa.string(),
    int: pa.int64(),
    float: pa.float64(),
    bool: pa.bool_(),
    datetime: pa.timestamp("us", tz="UTC"),
}


def _arrow_type(annotation: Any) -> tuple[pa.DataType, bool]:
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        inner = [a for a in get_args(annotation) if a is not type(None)]
        return _arrow_type(inner[0])[0], True
    if origin is list:
        return pa.list_(_arrow_type(get_args(annotation)[0])[0]), False
    return _SCALARS[annotation], False


@dataclass(frozen=True)
class TableContract:
    name: str
    version: int
    layer: Layer
    row: type[Row]
    description: str
    sort_by: tuple[str, ...]

    def arrow_schema(self) -> pa.Schema:
        fields = []
        for field_name, info in self.row.model_fields.items():
            arrow_type, nullable = _arrow_type(info.annotation)
            fields.append(pa.field(field_name, arrow_type, nullable=nullable))
        return pa.schema(fields)

    def validate_rows(self, rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [self.row.model_validate(dict(r)).model_dump() for r in rows]


CONTRACTS: tuple[TableContract, ...] = (
    TableContract(
        "images",
        1,
        "silver",
        SilverImage,
        "Normalised, EXIF-free images with dedupe links",
        ("ingested_at", "image_sha256"),
    ),
    TableContract(
        "holds",
        1,
        "silver",
        SilverHold,
        "Detected holds per analysis (latest detection)",
        ("analysis_id", "hold_id"),
    ),
    TableContract(
        "problems",
        1,
        "silver",
        SilverProblem,
        "Problem the climber selected per analysis",
        ("analysis_id",),
    ),
    TableContract(
        "betas",
        1,
        "silver",
        SilverBeta,
        "One row per generated or failed beta",
        ("created_at", "beta_id"),
    ),
    TableContract(
        "moves",
        1,
        "silver",
        SilverMove,
        "One row per move of a generated beta",
        ("beta_id", "move_index"),
    ),
    TableContract(
        "motion_specs",
        1,
        "silver",
        SilverMotionSpec,
        "One row per directed route video",
        ("directed_at", "video_id"),
    ),
    TableContract(
        "keyframes",
        1,
        "silver",
        SilverKeyframe,
        "One row per keyframe of a MotionSpec",
        ("video_id", "move_index"),
    ),
    TableContract(
        "feedback",
        1,
        "silver",
        SilverFeedback,
        "Climber feedback and playback signals",
        ("created_at", "feedback_id"),
    ),
    TableContract(
        "renders", 1, "silver", SilverRender, "Render outcomes per video", ("at", "video_id")
    ),
    TableContract(
        "beta_quality", 1, "gold", GoldBetaQuality, "Usefulness of betas by planner", ("planner",)
    ),
    TableContract(
        "confusing_moves", 1, "gold", GoldConfusingMove, "Moves climbers rewatch or flag", ()
    ),
)


def contract(name: str) -> TableContract:
    for c in CONTRACTS:
        if c.name == name:
            return c
    raise KeyError(f"no table contract named {name!r}")
