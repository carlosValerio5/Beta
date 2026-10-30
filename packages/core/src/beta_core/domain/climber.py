"""The climber and their body.

Segment ratios follow Drillis & Contini's anthropometric table (fractions of stature). Arm length
is then rescaled so that ``2 * arm + shoulder_width == wingspan`` to honour the ape index.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from beta_core.domain.base import DomainModel
from beta_core.domain.grades import Grade

SHOULDER_WIDTH = 0.259
HIP_WIDTH = 0.191
TORSO = 0.288  # hip joint centre -> shoulder joint centre (0.818H - 0.530H)
THIGH = 0.245
SHIN = 0.285  # knee -> sole, foot height included
HEAD_RADIUS = 0.065
UPPER_ARM_SHARE = 0.186 / (0.186 + 0.146 + 0.108)  # upper arm / (upper arm + forearm + hand)


class ClimbingStyle(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    BALANCED = "balanced"


class ClimberProfile(DomainModel):
    height_cm: float = Field(ge=120, le=230)
    ape_index_cm: float = Field(default=0, ge=-20, le=30)
    max_grade: Grade = Field(default_factory=lambda: Grade(v=3))
    style: ClimbingStyle = ClimbingStyle.BALANCED

    @property
    def wingspan_cm(self) -> float:
        return self.height_cm + self.ape_index_cm


class BodyModel(DomainModel):
    """Segment lengths of a 2D climber. ``unit`` is ``cm`` from a profile, ``px`` once scaled."""

    unit: Literal["cm", "px"] = "cm"
    height: float = Field(gt=0)
    shoulder_width: float = Field(gt=0)
    hip_width: float = Field(gt=0)
    torso: float = Field(gt=0)
    upper_arm: float = Field(gt=0)
    forearm: float = Field(gt=0)
    thigh: float = Field(gt=0)
    shin: float = Field(gt=0)
    head_radius: float = Field(gt=0)

    @classmethod
    def from_profile(cls, profile: ClimberProfile) -> BodyModel:
        h = profile.height_cm
        shoulder_width = SHOULDER_WIDTH * h
        arm = (profile.wingspan_cm - shoulder_width) / 2
        return cls(
            height=h,
            shoulder_width=shoulder_width,
            hip_width=HIP_WIDTH * h,
            torso=TORSO * h,
            upper_arm=arm * UPPER_ARM_SHARE,
            forearm=arm * (1 - UPPER_ARM_SHARE),
            thigh=THIGH * h,
            shin=SHIN * h,
            head_radius=HEAD_RADIUS * h,
        )

    @property
    def arm_length(self) -> float:
        return self.upper_arm + self.forearm

    @property
    def leg_length(self) -> float:
        return self.thigh + self.shin

    def scaled(self, px_per_cm: float) -> BodyModel:
        if self.unit != "cm":
            raise ValueError("only a body measured in cm can be scaled to pixels")
        if px_per_cm <= 0:
            raise ValueError("px_per_cm must be positive")
        lengths = self.model_dump(exclude={"unit"})
        return BodyModel(unit="px", **{k: v * px_per_cm for k, v in lengths.items()})
