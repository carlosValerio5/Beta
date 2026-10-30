"""2D geometry in the pixel space of the normalised image (origin top-left, y grows downward)."""

from __future__ import annotations

import math

from pydantic import Field

from beta_core.domain.base import DomainModel


class Point(DomainModel):
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def midpoint(self, other: Point) -> Point:
        return Point(x=(self.x + other.x) / 2, y=(self.y + other.y) / 2)

    def translate(self, dx: float, dy: float) -> Point:
        return Point(x=self.x + dx, y=self.y + dy)


class BBox(DomainModel):
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)

    @property
    def center(self) -> Point:
        return Point(x=self.x + self.w / 2, y=self.y + self.h / 2)

    @property
    def area(self) -> float:
        return self.w * self.h

    def contains(self, point: Point) -> bool:
        return self.x <= point.x <= self.x + self.w and self.y <= point.y <= self.y + self.h
