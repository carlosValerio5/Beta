import math

import pytest

from beta_core.domain.beta import Limb
from beta_core.domain.climber import BodyModel, ClimberProfile
from beta_core.domain.geometry import Point
from beta_core.kinematics import (
    best_hip,
    kinematics_fixtures,
    limb_roots,
    max_reach_ratio,
    solve_two_bone,
)


def P(x: float, y: float) -> Point:
    return Point(x=x, y=y)


@pytest.fixture
def body_px() -> BodyModel:
    return BodyModel.from_profile(ClimberProfile(height_cm=175)).scaled(3.0)


def test_limb_roots_upright_without_hands(body_px: BodyModel) -> None:
    roots = limb_roots(P(500, 1000), body_px, hand_targets=[])
    assert roots[Limb.LH].x < roots[Limb.RH].x
    assert roots[Limb.LH].y == pytest.approx(1000 - body_px.torso)
    assert roots[Limb.LF].y == pytest.approx(1000)
    assert roots[Limb.LF].x < roots[Limb.RF].x


def test_limb_roots_tilt_toward_hands(body_px: BodyModel) -> None:
    roots = limb_roots(P(500, 1000), body_px, hand_targets=[P(900, 800)])
    shoulder_mid = roots[Limb.LH].midpoint(roots[Limb.RH])
    assert shoulder_mid.x > 500
    assert P(500, 1000).distance_to(shoulder_mid) == pytest.approx(body_px.torso)


def test_solve_two_bone_reachable() -> None:
    sol = solve_two_bone(P(0, 0), P(3, 4), 3, 3, bend=1)
    assert sol.reached
    assert sol.end == P(3, 4)
    assert P(0, 0).distance_to(sol.joint) == pytest.approx(3)
    assert sol.joint.distance_to(sol.end) == pytest.approx(3)


def test_solve_two_bone_unreachable_points_at_target() -> None:
    sol = solve_two_bone(P(0, 0), P(10, 0), 3, 3, bend=1)
    assert not sol.reached
    assert sol.end.x == pytest.approx(6)
    assert sol.end.y == pytest.approx(0)


def test_solve_two_bone_bend_mirrors_joint() -> None:
    a = solve_two_bone(P(0, 0), P(4, 0), 3, 3, bend=1)
    b = solve_two_bone(P(0, 0), P(4, 0), 3, 3, bend=-1)
    assert a.joint.x == pytest.approx(b.joint.x)
    assert a.joint.y == pytest.approx(-b.joint.y)


def test_solve_two_bone_target_at_root_does_not_crash() -> None:
    sol = solve_two_bone(P(1, 1), P(1, 1), 3, 2, bend=1)
    assert math.isfinite(sol.joint.x)


def test_best_hip_finds_feasible_start_pose(body_px: BodyModel) -> None:
    points = {
        Limb.LH: P(450, 1050),
        Limb.RH: P(560, 1050),
        Limb.LF: P(430, 1350),
        Limb.RF: P(580, 1350),
    }
    hip, ratio = best_hip(points, body_px)
    assert ratio <= 1.0
    assert max_reach_ratio(hip, points, body_px) == pytest.approx(ratio)


def test_best_hip_reports_infeasible(body_px: BodyModel) -> None:
    points = {Limb.LH: P(500, 0), Limb.LF: P(500, 3000)}
    _, ratio = best_hip(points, body_px)
    assert ratio > 1.5


def test_max_reach_ratio_ignores_free_limbs(body_px: BodyModel) -> None:
    hip = P(500, 1000)
    points: dict[Limb, Point | None] = {
        Limb.LH: None,
        Limb.RH: None,
        Limb.LF: P(480, 1100),
        Limb.RF: None,
    }
    assert max_reach_ratio(hip, points, body_px) < 1.0


def test_fixtures_are_deterministic() -> None:
    first = kinematics_fixtures()
    assert first == kinematics_fixtures()
    assert len(first["two_bone"]) >= 5
    assert {"root", "target", "l1", "l2", "bend", "joint", "end", "reached"} <= set(
        first["two_bone"][0]
    )
    assert len(first["limb_roots"]) >= 2


def test_natural_hip_hangs_off_straighter_arms(body_px: BodyModel) -> None:
    from beta_core.kinematics import natural_hip

    points = {
        Limb.LH: P(450, 1050),
        Limb.RH: P(560, 1050),
        Limb.LF: P(430, 1350),
        Limb.RF: P(580, 1350),
    }
    compact, _ = best_hip(points, body_px)
    natural = natural_hip(points, body_px)
    assert max_reach_ratio(natural, points, body_px) <= 1.0
    assert natural.y > compact.y  # hips sit lower, arms extend
    assert natural == natural_hip(points, body_px)


def test_natural_hip_falls_back_when_nothing_is_comfortable(body_px: BodyModel) -> None:
    from beta_core.kinematics import natural_hip

    points = {Limb.LH: P(500, 0), Limb.LF: P(500, 3000)}
    assert natural_hip(points, body_px) == best_hip(points, body_px)[0]
