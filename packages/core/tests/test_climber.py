import pytest
from pydantic import ValidationError

from beta_core.domain.climber import BodyModel, ClimberProfile


def test_wingspan_includes_ape_index() -> None:
    assert ClimberProfile(height_cm=170, ape_index_cm=4).wingspan_cm == 174


def test_profile_bounds() -> None:
    with pytest.raises(ValidationError):
        ClimberProfile(height_cm=90)


def test_arm_segments_sum_to_wingspan() -> None:
    body = BodyModel.from_profile(ClimberProfile(height_cm=175, ape_index_cm=0))
    assert body.unit == "cm"
    assert 2 * body.arm_length + body.shoulder_width == pytest.approx(175)


def test_leg_length_is_hip_height() -> None:
    body = BodyModel.from_profile(ClimberProfile(height_cm=175))
    assert body.leg_length == pytest.approx(0.53 * 175)


def test_positive_ape_index_lengthens_arms() -> None:
    neutral = BodyModel.from_profile(ClimberProfile(height_cm=175, ape_index_cm=0))
    plus = BodyModel.from_profile(ClimberProfile(height_cm=175, ape_index_cm=8))
    assert plus.arm_length == pytest.approx(neutral.arm_length + 4)


def test_scaled_to_pixels() -> None:
    body = BodyModel.from_profile(ClimberProfile(height_cm=175))
    px = body.scaled(3.0)
    assert px.unit == "px"
    assert px.arm_length == pytest.approx(body.arm_length * 3)
    assert px.torso == pytest.approx(body.torso * 3)


def test_cannot_scale_twice() -> None:
    px = BodyModel.from_profile(ClimberProfile(height_cm=175)).scaled(3.0)
    with pytest.raises(ValueError, match="cm"):
        px.scaled(2.0)
