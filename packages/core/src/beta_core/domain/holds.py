from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from beta_core.domain.base import DomainModel
from beta_core.domain.geometry import BBox, Point
from beta_core.errors import UnknownHoldError

HoldRole = Literal["start", "top", "route"]


class HoldType(StrEnum):
    JUG = "jug"
    CRIMP = "crimp"
    SLOPER = "sloper"
    PINCH = "pinch"
    POCKET = "pocket"
    EDGE = "edge"
    VOLUME = "volume"
    FOOTHOLD = "foothold"
    UNKNOWN = "unknown"


class Hold(DomainModel):
    id: int = Field(ge=0)
    bbox: BBox
    color: str = Field(min_length=1, max_length=32)
    hold_type: HoldType = HoldType.UNKNOWN
    confidence: float = Field(default=1.0, ge=0, le=1)

    @property
    def center(self) -> Point:
        return self.bbox.center

    @property
    def size(self) -> float:
        return max(self.bbox.w, self.bbox.h)


class Problem(DomainModel):
    """The holds a climber selected as one boulder problem, with its start and top."""

    holds: tuple[Hold, ...] = Field(min_length=2)
    start_hold_ids: tuple[int, ...] = Field(min_length=1, max_length=2)
    top_hold_id: int
    color: str | None = None

    @model_validator(mode="after")
    def _check_ids(self) -> Problem:
        ids = [h.id for h in self.holds]
        if len(ids) != len(set(ids)):
            raise ValueError("hold ids must be unique")
        known = set(ids)
        if len(set(self.start_hold_ids)) != len(self.start_hold_ids):
            raise ValueError("start holds must be distinct")
        if not set(self.start_hold_ids) <= known:
            raise ValueError("start holds must be part of the problem")
        if self.top_hold_id not in known:
            raise ValueError("top hold must be part of the problem")
        if self.top_hold_id in self.start_hold_ids:
            raise ValueError("top hold cannot also be a start hold")
        return self

    @property
    def hold_ids(self) -> frozenset[int]:
        return frozenset(h.id for h in self.holds)

    def hold(self, hold_id: int) -> Hold:
        for h in self.holds:
            if h.id == hold_id:
                return h
        raise UnknownHoldError(hold_id)

    def role_of(self, hold_id: int) -> HoldRole:
        if hold_id in self.start_hold_ids:
            return "start"
        if hold_id == self.top_hold_id:
            return "top"
        return "route"
