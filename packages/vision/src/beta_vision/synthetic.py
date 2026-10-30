"""Seeded synthetic bouldering walls with ground truth.

Used for tests, seed data (bronze), the offline golden set and renderer fixtures. A wall is a grey
textured panel with bolt-hole t-nuts and seams, one *problem* laid out as a climbable ladder (start
pair, intermediate feet, alternating hand holds, a top jug) and distractor holds in other colours.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from beta_core.domain.geometry import BBox, Point
from beta_core.domain.holds import Hold, HoldType, Problem
from beta_core.palette import HOLD_COLORS, hex_to_rgb

WALL_RGB = (150, 150, 148)
TNUT_RGB = (92, 92, 90)
SEAM_RGB = (120, 120, 118)
MIN_GAP_PX = 14.0


@dataclass(frozen=True)
class SyntheticWall:
    seed: int
    image: bytes
    width: int
    height: int
    holds: tuple[Hold, ...]
    problem_color: str
    start_hold_ids: tuple[int, ...]
    top_hold_id: int
    foot_hold_ids: tuple[int, ...]
    px_per_cm: float

    def problem(self) -> Problem:
        return Problem(
            holds=tuple(h for h in self.holds if h.color == self.problem_color),
            start_hold_ids=self.start_hold_ids,
            top_hold_id=self.top_hold_id,
            color=self.problem_color,
        )


class SyntheticWallGenerator:
    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    # -------------------------------------------------------------- public

    def generate(
        self,
        width: int = 1000,
        height: int = 1500,
        problem_color: str = "yellow",
        n_hand_holds: int = 5,
        n_distractors: int = 18,
        px_per_cm: float = 3.0,
    ) -> SyntheticWall:
        polys: list[tuple[list[tuple[float, float]], str, HoldType]] = []

        def place(cx: float, cy: float, radius: float, color: str, kind: HoldType) -> int | None:
            poly = self._polygon(cx, cy, radius)
            if not self._fits(poly, polys, width, height):
                return None
            polys.append((poly, color, kind))
            return len(polys) - 1

        s = px_per_cm
        cx = width / 2 + float(self._rng.uniform(-60, 60))
        base_y = height * 0.74
        step = 38 * s

        starts = [
            self._must(place(cx - 20 * s, base_y, self._r(20, 24), problem_color, HoldType.JUG)),
            self._must(place(cx + 20 * s, base_y, self._r(20, 24), problem_color, HoldType.JUG)),
        ]
        feet = [
            self._must(
                place(
                    cx - 22 * s, base_y + 95 * s, self._r(10, 13), problem_color, HoldType.FOOTHOLD
                )
            ),
            self._must(
                place(
                    cx + 22 * s, base_y + 95 * s, self._r(10, 13), problem_color, HoldType.FOOTHOLD
                )
            ),
            self._must(
                place(
                    cx - 18 * s, base_y + 50 * s, self._r(10, 13), problem_color, HoldType.FOOTHOLD
                )
            ),
            self._must(
                place(
                    cx + 18 * s, base_y + 50 * s, self._r(10, 13), problem_color, HoldType.FOOTHOLD
                )
            ),
        ]
        for k in range(1, n_hand_holds + 1):
            side = -1 if k % 2 else 1
            x = cx + side * float(self._rng.uniform(15, 25)) * s
            y = base_y - k * step + float(self._rng.uniform(-8, 8))
            self._must(place(x, y, self._r(16, 24), problem_color, HoldType.UNKNOWN))
        top = self._must(
            place(
                cx, base_y - (n_hand_holds + 1) * step, self._r(20, 24), problem_color, HoldType.JUG
            )
        )

        others = [c for c in HOLD_COLORS if c != problem_color]
        placed = attempts = 0
        while placed < n_distractors and attempts < n_distractors * 40:
            attempts += 1
            color = others[int(self._rng.integers(len(others)))]
            x = float(self._rng.uniform(40, width - 40))
            y = float(self._rng.uniform(80, height - 60))
            if place(x, y, self._r(12, 24), color, HoldType.UNKNOWN) is not None:
                placed += 1

        holds = tuple(
            Hold(id=i, bbox=self._bbox(poly, width, height), color=color, hold_type=kind)
            for i, (poly, color, kind) in enumerate(polys)
        )
        return SyntheticWall(
            seed=self.seed,
            image=self._draw(width, height, polys),
            width=width,
            height=height,
            holds=holds,
            problem_color=problem_color,
            start_hold_ids=tuple(starts),
            top_hold_id=top,
            foot_hold_ids=tuple(feet),
            px_per_cm=px_per_cm,
        )

    # -------------------------------------------------------------- geometry

    def _r(self, lo: float, hi: float) -> float:
        return float(self._rng.uniform(lo, hi))

    def _polygon(self, cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
        n = int(self._rng.integers(8, 12))
        phase = float(self._rng.uniform(0, 2 * math.pi))
        pts = []
        for i in range(n):
            angle = phase + 2 * math.pi * i / n + float(self._rng.uniform(-0.15, 0.15))
            r = radius * float(self._rng.uniform(0.78, 1.12))
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return pts

    @staticmethod
    def _bbox(poly: list[tuple[float, float]], width: int, height: int) -> BBox:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, y0 = max(min(xs), 0.0), max(min(ys), 0.0)
        x1, y1 = min(max(xs), float(width)), min(max(ys), float(height))
        return BBox(x=x0, y=y0, w=max(x1 - x0, 1.0), h=max(y1 - y0, 1.0))

    def _fits(
        self,
        poly: list[tuple[float, float]],
        existing: list[tuple[list[tuple[float, float]], str, HoldType]],
        width: int,
        height: int,
    ) -> bool:
        box = self._bbox(poly, width, height)
        if box.x <= 2 or box.y <= 2 or box.x + box.w >= width - 2 or box.y + box.h >= height - 2:
            return False
        size = max(box.w, box.h)
        for other_poly, _, _ in existing:
            other = self._bbox(other_poly, width, height)
            gap = box.center.distance_to(other.center) - (size + max(other.w, other.h)) / 2
            if gap < MIN_GAP_PX:
                return False
        return True

    @staticmethod
    def _must(index: int | None) -> int:
        if index is None:
            raise RuntimeError("problem hold could not be placed; use a larger wall")
        return index

    # -------------------------------------------------------------- drawing

    def _draw(
        self, width: int, height: int, polys: list[tuple[list[tuple[float, float]], str, HoldType]]
    ) -> bytes:
        base = np.empty((height, width, 3), dtype=np.float64)
        base[:] = WALL_RGB
        base += self._rng.normal(0, 6, size=(height, width, 1))
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
        draw = ImageDraw.Draw(img)

        for y in range(250, height, 250):
            draw.line([(0, y), (width, y)], fill=SEAM_RGB, width=2)
        for x in range(250, width, 250):
            draw.line([(x, 0), (x, height)], fill=SEAM_RGB, width=2)
        for y in range(25, height, 50):
            for x in range(25, width, 50):
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=TNUT_RGB)

        for poly, color, _ in polys:
            rgb = hex_to_rgb(HOLD_COLORS[color])
            dark = tuple(int(c * 0.75) for c in rgb)
            light = tuple(int(c + (255 - c) * 0.3) for c in rgb)
            draw.polygon(poly, fill=rgb, outline=dark, width=2)
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            r = min(math.dist((cx, cy), p) for p in poly) * 0.35
            draw.ellipse([cx - r - 2, cy - r - 3, cx + r - 2, cy + r - 3], fill=light)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()


def centroid(hold: Hold) -> Point:
    return hold.center
