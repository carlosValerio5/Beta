from __future__ import annotations

import pytest

from beta_core.domain.beta import BetaPlan
from beta_core.domain.climber import BodyModel, ClimberProfile
from beta_core.domain.holds import Problem
from beta_core.testing import LADDER_PX_PER_CM, ladder_plan, ladder_problem, profile_175


@pytest.fixture
def problem() -> Problem:
    return ladder_problem()


@pytest.fixture
def plan() -> BetaPlan:
    return ladder_plan()


@pytest.fixture
def profile() -> ClimberProfile:
    return profile_175()


@pytest.fixture
def body_cm(profile: ClimberProfile) -> BodyModel:
    return BodyModel.from_profile(profile)


@pytest.fixture
def px_per_cm() -> float:
    return LADDER_PX_PER_CM
