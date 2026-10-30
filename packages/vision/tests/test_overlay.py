from __future__ import annotations

import io

import numpy as np
from PIL import Image

from beta_core.ports import NormalizedImage
from beta_core.testing import ladder_plan, ladder_problem
from beta_vision.overlay import PillowMarkRenderer, render_beta_poster
from beta_vision.synthetic import SyntheticWall


def pixels(data: bytes) -> np.ndarray:  # type: ignore[type-arg]
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.int16)


def test_marks_keep_size_and_change_pixels(wall: SyntheticWall, wall_image: NormalizedImage) -> None:
    problem = wall.problem()
    marked = PillowMarkRenderer().render_marks(wall_image, problem.holds)
    assert (marked.width, marked.height) == (wall_image.width, wall_image.height)
    assert marked.sha256 != wall_image.sha256
    diff = np.abs(pixels(marked.data) - pixels(wall_image.data)).sum(axis=2)
    for hold in problem.holds:
        x, y = int(hold.center.x), int(hold.center.y)
        r = int(hold.size)
        region = diff[max(0, y - r) : y + r, max(0, x - r) : x + r]
        assert region.max() > 100, f"no marker drawn near hold {hold.id}"


def test_poster_renders_plan(wall_image: NormalizedImage) -> None:
    poster = render_beta_poster(wall_image, ladder_plan(), ladder_problem())
    img = Image.open(io.BytesIO(poster))
    assert img.format == "JPEG"
    assert img.size == (wall_image.width, wall_image.height)
