import pytest
from pydantic import ValidationError

from beta_core.domain.geometry import BBox, Point


def test_point_distance() -> None:
    assert Point(x=0, y=0).distance_to(Point(x=3, y=4)) == 5


def test_point_midpoint() -> None:
    assert Point(x=0, y=0).midpoint(Point(x=2, y=4)) == Point(x=1, y=2)


def test_point_is_frozen() -> None:
    p = Point(x=1, y=1)
    with pytest.raises(ValidationError):
        p.x = 2  # type: ignore[misc]


def test_bbox_center_and_area() -> None:
    box = BBox(x=10, y=20, w=30, h=40)
    assert box.center == Point(x=25, y=40)
    assert box.area == 1200


def test_bbox_rejects_non_positive_size() -> None:
    with pytest.raises(ValidationError):
        BBox(x=0, y=0, w=0, h=1)


def test_bbox_contains() -> None:
    box = BBox(x=0, y=0, w=10, h=10)
    assert box.contains(Point(x=5, y=5))
    assert not box.contains(Point(x=11, y=5))
