import pytest
from pydantic import ValidationError

from beta_core.domain.geometry import BBox, Point
from beta_core.domain.holds import Hold, HoldType, Problem
from beta_core.errors import UnknownHoldError


def hold(i: int, x: float, y: float, color: str = "red") -> Hold:
    return Hold(id=i, bbox=BBox(x=x - 20, y=y - 20, w=40, h=40), color=color)


def test_hold_defaults_and_center() -> None:
    h = hold(1, 100, 200)
    assert h.center == Point(x=100, y=200)
    assert h.hold_type is HoldType.UNKNOWN
    assert h.confidence == 1.0


def test_problem_lookup() -> None:
    p = Problem(
        holds=(hold(0, 0, 100), hold(1, 0, 50), hold(2, 0, 0)), start_hold_ids=(0,), top_hold_id=2
    )
    assert p.hold(2).id == 2
    assert p.hold_ids == frozenset({0, 1, 2})


def test_problem_unknown_hold_raises() -> None:
    p = Problem(holds=(hold(0, 0, 100), hold(1, 0, 0)), start_hold_ids=(0,), top_hold_id=1)
    with pytest.raises(UnknownHoldError):
        p.hold(9)


@pytest.mark.parametrize(
    ("holds", "starts", "top"),
    [
        ((hold(0, 0, 0), hold(0, 0, 10)), (0,), 0),  # duplicate ids
        ((hold(0, 0, 0), hold(1, 0, 10)), (5,), 1),  # unknown start
        ((hold(0, 0, 0), hold(1, 0, 10)), (0,), 7),  # unknown top
        (
            (hold(0, 0, 0), hold(1, 0, 10), hold(2, 0, 20), hold(3, 0, 30)),
            (0, 1, 2),
            3,
        ),  # >2 starts
        ((hold(0, 0, 0), hold(1, 0, 10)), (0,), 0),  # top is a start hold
        ((hold(0, 0, 0), hold(1, 0, 10)), (), 1),  # no start
    ],
)
def test_problem_rejects_invalid(
    holds: tuple[Hold, ...], starts: tuple[int, ...], top: int
) -> None:
    with pytest.raises(ValidationError):
        Problem(holds=holds, start_hold_ids=starts, top_hold_id=top)


def test_problem_role_of(problem: Problem) -> None:
    assert problem.role_of(problem.start_hold_ids[0]) == "start"
    assert problem.role_of(problem.top_hold_id) == "top"
    assert problem.role_of(4) == "route"
