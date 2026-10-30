from __future__ import annotations

import io
import itertools

from PIL import Image

from beta_vision.synthetic import SyntheticWall, SyntheticWallGenerator


def test_deterministic_by_seed() -> None:
    a = SyntheticWallGenerator(seed=3).generate()
    b = SyntheticWallGenerator(seed=3).generate()
    c = SyntheticWallGenerator(seed=4).generate()
    assert a.image == b.image
    assert a.holds == b.holds
    assert a.image != c.image


def test_image_matches_requested_size(wall: SyntheticWall) -> None:
    img = Image.open(io.BytesIO(wall.image))
    assert img.size == (wall.width, wall.height)
    assert img.format == "JPEG"


def test_problem_is_valid_and_single_coloured(wall: SyntheticWall) -> None:
    problem = wall.problem()
    assert {h.color for h in problem.holds} == {wall.problem_color}
    top = problem.hold(problem.top_hold_id)
    assert top.center.y == min(h.center.y for h in problem.holds)
    starts = [problem.hold(i) for i in problem.start_hold_ids]
    hand_holds = [h for h in problem.holds if h.id not in wall.foot_hold_ids]
    assert max(s.center.y for s in starts) >= max(h.center.y for h in hand_holds) - 1


def test_holds_do_not_overlap(wall: SyntheticWall) -> None:
    for a, b in itertools.combinations(wall.holds, 2):
        assert a.center.distance_to(b.center) >= a.size / 2 + b.size / 2


def test_has_distractors_in_other_colours(wall: SyntheticWall) -> None:
    others = {h.color for h in wall.holds} - {wall.problem_color}
    assert len(others) >= 2
