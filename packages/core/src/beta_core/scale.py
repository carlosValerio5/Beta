"""Pixel ↔ centimetre scale estimation for a single wall photo."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import Field

from beta_core.domain.base import DomainModel

if TYPE_CHECKING:
    from beta_core.domain.holds import Hold

#: Median longest side of a hand hold on a commercial wall.
TYPICAL_HOLD_CM = 12.0
#: Typical bouldering wall height when nothing else is known.
DEFAULT_WALL_CM = 450.0
MIN_HOLDS_FOR_SIZE_ESTIMATE = 3


class ScaleMethod(StrEnum):
    WALL_HEIGHT = "wall_height"
    HOLD_SIZE = "hold_size"
    DEFAULT = "default"


class ScaleEstimate(DomainModel):
    px_per_cm: float = Field(gt=0)
    method: ScaleMethod
    confidence: float = Field(ge=0, le=1)


def estimate_px_per_cm(
    holds: Sequence[Hold], image_height_px: int, wall_height_cm: float | None = None
) -> ScaleEstimate:
    if wall_height_cm is not None:
        if wall_height_cm <= 0:
            raise ValueError("wall_height_cm must be positive")
        return ScaleEstimate(
            px_per_cm=image_height_px / wall_height_cm,
            method=ScaleMethod.WALL_HEIGHT,
            confidence=0.7,
        )
    if len(holds) >= MIN_HOLDS_FOR_SIZE_ESTIMATE:
        median_px = statistics.median(h.size for h in holds)
        return ScaleEstimate(
            px_per_cm=median_px / TYPICAL_HOLD_CM, method=ScaleMethod.HOLD_SIZE, confidence=0.4
        )
    return ScaleEstimate(
        px_per_cm=image_height_px / DEFAULT_WALL_CM, method=ScaleMethod.DEFAULT, confidence=0.1
    )
