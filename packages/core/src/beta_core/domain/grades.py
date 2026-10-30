"""Bouldering grades: V-scale is canonical, Fontainebleau is derived."""

from __future__ import annotations

from functools import total_ordering
from typing import Any

from pydantic import Field

from beta_core.domain.base import DomainModel

_FONT_BY_V: dict[int, str] = {
    -1: "3",
    0: "4",
    1: "5",
    2: "5+",
    3: "6A",
    4: "6B",
    5: "6C",
    6: "7A",
    7: "7A+",
    8: "7B",
    9: "7C",
    10: "7C+",
    11: "8A",
    12: "8A+",
    13: "8B",
    14: "8B+",
    15: "8C",
    16: "8C+",
    17: "9A",
}
# Common "in between" Font grades rounded to the nearest V grade.
_V_BY_FONT: dict[str, int] = {font: v for v, font in _FONT_BY_V.items()} | {
    "3+": -1,
    "4+": 0,
    "6A+": 3,
    "6B+": 4,
    "6C+": 5,
    "7B+": 8,
}
MIN_V = -1
MAX_V = 17


@total_ordering
class Grade(DomainModel):
    """A boulder grade. ``v == -1`` is VB."""

    v: int = Field(ge=MIN_V, le=MAX_V)

    @classmethod
    def parse(cls, text: str) -> Grade:
        cleaned = text.strip().upper()
        if cleaned.startswith("V"):
            rest = cleaned[1:]
            if rest == "B":
                return cls(v=-1)
            if rest.isdigit():
                v = int(rest)
                if MIN_V <= v <= MAX_V:
                    return cls(v=v)
                raise ValueError(f"grade {text!r} is out of range V0-V17")
        if cleaned in _V_BY_FONT:
            return cls(v=_V_BY_FONT[cleaned])
        raise ValueError(f"unrecognised grade {text!r}")

    @property
    def font(self) -> str:
        return _FONT_BY_V[self.v]

    def __str__(self) -> str:
        return "VB" if self.v == -1 else f"V{self.v}"

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Grade):
            return NotImplemented
        return self.v < other.v
