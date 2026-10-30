import pytest

from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold
from beta_core.scale import ScaleMethod, estimate_px_per_cm


def holds_of_size(px: float, n: int = 5) -> list[Hold]:
    return [Hold(id=i, bbox=BBox(x=i * 100, y=0, w=px, h=px * 0.8), color="red") for i in range(n)]


def test_wall_height_wins() -> None:
    est = estimate_px_per_cm(holds_of_size(36), image_height_px=1500, wall_height_cm=500)
    assert est.px_per_cm == pytest.approx(3.0)
    assert est.method is ScaleMethod.WALL_HEIGHT


def test_hold_size_median() -> None:
    est = estimate_px_per_cm(holds_of_size(36), image_height_px=1500)
    assert est.px_per_cm == pytest.approx(3.0)
    assert est.method is ScaleMethod.HOLD_SIZE


def test_default_without_enough_holds() -> None:
    est = estimate_px_per_cm(holds_of_size(36, n=2), image_height_px=1500)
    assert est.px_per_cm == pytest.approx(1500 / 450)
    assert est.method is ScaleMethod.DEFAULT
    assert est.confidence < 0.2


def test_rejects_non_positive_wall_height() -> None:
    with pytest.raises(ValueError, match="wall_height"):
        estimate_px_per_cm([], image_height_px=1500, wall_height_cm=0)
