from __future__ import annotations

import pytest

from beta_core.ports import NormalizedImage
from beta_vision.preprocess import PillowPreprocessor
from beta_vision.synthetic import SyntheticWall, SyntheticWallGenerator


@pytest.fixture(scope="session")
def wall() -> SyntheticWall:
    return SyntheticWallGenerator(seed=7).generate()


@pytest.fixture(scope="session")
def wall_image(wall: SyntheticWall) -> NormalizedImage:
    return PillowPreprocessor().normalize(wall.image)
