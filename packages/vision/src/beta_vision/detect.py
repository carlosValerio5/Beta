"""Colour-segmentation hold detector (v0, ADR-0005).

Gym holds are saturated; walls, t-nuts and chalk are not. We threshold saturation/value in HSV,
clean the mask morphologically, and turn each blob into a :class:`Hold` with a colour label (circular
mean hue) and a coarse shape-based type. White/black holds are not detected in v0 — the climber adds
them by tapping. A learned detector will replace this behind the same ``HoldDetector`` port.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import cv2
import numpy as np

from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold, HoldType
from beta_core.errors import InvalidInputError
from beta_core.ports import NormalizedImage

#: OpenCV hue (0-179) ranges → colour label.
HUE_BINS: tuple[tuple[float, float, str], ...] = (
    (0, 8, "red"),
    (8, 20, "orange"),
    (20, 35, "yellow"),
    (35, 85, "green"),
    (85, 130, "blue"),
    (130, 155, "purple"),
    (155, 170, "pink"),
    (170, 180, "red"),
)


def color_label(hues: Any) -> str:
    """Circular mean of OpenCV hues (0-179 ⇒ 0-358°) mapped to a label."""
    angles = np.asarray(hues, dtype=np.float64) * (math.pi / 90.0)
    mean = math.atan2(float(np.sin(angles).mean()), float(np.cos(angles).mean()))
    hue = (math.degrees(mean) % 360.0) / 2.0
    for lo, hi, name in HUE_BINS:
        if lo <= hue < hi:
            return name
    return "red"


def shape_type(area_frac: float, w: float, h: float) -> HoldType:
    aspect = max(w, h) / max(min(w, h), 1.0)
    if area_frac >= 0.006:
        return HoldType.VOLUME
    if aspect >= 2.2:
        return HoldType.EDGE
    if area_frac < 0.00035:
        return HoldType.FOOTHOLD
    if area_frac >= 0.0012:
        return HoldType.JUG
    return HoldType.UNKNOWN


class ColorHoldDetector:
    version = "color-hsv@1"
    ROW_BAND_PX = 40

    def __init__(
        self,
        sat_threshold: int = 90,
        val_threshold: int = 70,
        min_area_frac: float = 0.00012,
        max_area_frac: float = 0.05,
    ) -> None:
        self.sat_threshold = sat_threshold
        self.val_threshold = val_threshold
        self.min_area_frac = min_area_frac
        self.max_area_frac = max_area_frac

    @classmethod
    def row_band(cls, hold: Hold) -> int:
        return int(hold.center.y // cls.ROW_BAND_PX)

    def detect(self, image: NormalizedImage) -> list[Hold]:
        bgr = cv2.imdecode(np.frombuffer(image.data, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            raise InvalidInputError("image could not be decoded for detection")
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        hue, sat, val = cv2.split(hsv)
        mask: Any = ((sat >= self.sat_threshold) & (val >= self.val_threshold)).astype(
            np.uint8
        ) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_h, img_w = mask.shape
        image_area = float(img_w * img_h)
        found: list[tuple[float, float, float, float, str, HoldType, float]] = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            area_frac = area / image_area
            if not self.min_area_frac <= area_frac <= self.max_area_frac:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            hull_area = float(cv2.contourArea(cv2.convexHull(contour)))
            solidity = area / hull_area if hull_area > 0 else 0.0

            blob = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(blob, [contour - np.array([x, y])], -1, 255, thickness=-1)
            inside = (blob > 0) & (mask[y : y + h, x : x + w] > 0)
            hues = hue[y : y + h, x : x + w][inside]
            if hues.size == 0:
                continue
            found.append(
                (
                    float(x),
                    float(y),
                    float(w),
                    float(h),
                    color_label(hues),
                    shape_type(area_frac, w, h),
                    round(min(max(solidity, 0.0), 1.0), 3),
                )
            )

        found.sort(key=lambda f: (int((f[1] + f[3] / 2) // self.ROW_BAND_PX), f[0] + f[2] / 2))
        return [
            Hold(id=i, bbox=BBox(x=x, y=y, w=w, h=h), color=color, hold_type=kind, confidence=conf)
            for i, (x, y, w, h, color, kind, conf) in enumerate(found)
        ]


def match_holds(
    truth: Sequence[Hold], found: Sequence[Hold], max_distance: float
) -> list[tuple[Hold, Hold]]:
    """Greedy one-to-one matching by centre distance (for evaluation)."""
    pairs = sorted(
        (t.center.distance_to(f.center), ti, fi)
        for ti, t in enumerate(truth)
        for fi, f in enumerate(found)
        if t.center.distance_to(f.center) <= max_distance
    )
    used_t: set[int] = set()
    used_f: set[int] = set()
    matches: list[tuple[Hold, Hold]] = []
    for _, ti, fi in pairs:
        if ti in used_t or fi in used_f:
            continue
        used_t.add(ti)
        used_f.add(fi)
        matches.append((truth[ti], found[fi]))
    return matches
