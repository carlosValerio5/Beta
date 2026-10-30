from __future__ import annotations

import io

from PIL import Image

from beta_core.domain.holds import Hold
from beta_core.ports import NormalizedImage
from beta_vision.detect import ColorHoldDetector, match_holds
from beta_vision.preprocess import PillowPreprocessor
from beta_vision.synthetic import SyntheticWall

MATCH_PX = 15.0


def test_recall_and_precision_on_synthetic_wall(
    wall: SyntheticWall, wall_image: NormalizedImage
) -> None:
    detected = ColorHoldDetector().detect(wall_image)
    matches = match_holds(wall.holds, detected, max_distance=MATCH_PX)
    recall = len(matches) / len(wall.holds)
    precision = len(matches) / len(detected)
    assert recall >= 0.9, f"recall {recall:.2f}"
    assert precision >= 0.9, f"precision {precision:.2f}"


def test_colour_labels(wall: SyntheticWall, wall_image: NormalizedImage) -> None:
    detected = ColorHoldDetector().detect(wall_image)
    matches = match_holds(wall.holds, detected, max_distance=MATCH_PX)
    correct = sum(1 for truth, found in matches if truth.color == found.color)
    assert correct / len(matches) >= 0.95


def test_ids_unique_and_read_top_to_bottom(wall_image: NormalizedImage) -> None:
    detected = ColorHoldDetector().detect(wall_image)
    assert [h.id for h in detected] == list(range(len(detected)))
    bands = [ColorHoldDetector.row_band(h) for h in detected]
    assert bands == sorted(bands)


def test_holds_are_inside_the_image(wall_image: NormalizedImage) -> None:
    for h in ColorHoldDetector().detect(wall_image):
        assert h.bbox.x >= 0
        assert h.bbox.x + h.bbox.w <= wall_image.width
        assert h.bbox.y >= 0
        assert h.bbox.y + h.bbox.h <= wall_image.height
        assert 0 <= h.confidence <= 1


def test_blank_wall_has_no_holds() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (600, 900), (150, 150, 148)).save(buf, format="JPEG")
    blank = PillowPreprocessor().normalize(buf.getvalue())
    assert ColorHoldDetector().detect(blank) == []


def test_version_is_recorded() -> None:
    assert ColorHoldDetector().version.startswith("color-hsv@")


def test_match_holds_is_one_to_one(wall: SyntheticWall) -> None:
    holds: list[Hold] = list(wall.holds)
    matches = match_holds(holds, holds + holds, max_distance=1.0)
    assert len(matches) == len(holds)
