from __future__ import annotations

from pathlib import Path

import pytest

from beta_core.domain.climber import BodyModel
from beta_core.ports import BetaRequest, MotionRequest
from beta_core.testing import (
    FAKE_IMAGE,
    LADDER_IMAGE,
    LADDER_PX_PER_CM,
    ladder_plan,
    ladder_problem,
    profile_175,
)
from beta_llm.prompts import PromptRegistry, default_prompts_dir

IMAGE = FAKE_IMAGE


@pytest.fixture
def registry() -> PromptRegistry:
    return PromptRegistry(default_prompts_dir())


@pytest.fixture
def beta_request() -> BetaRequest:
    profile = profile_175()
    return BetaRequest(
        plan_id="bet_1",
        analysis_id="ana_1",
        problem=ladder_problem(),
        image=IMAGE,
        profile=profile,
        body=BodyModel.from_profile(profile),
        px_per_cm=LADDER_PX_PER_CM,
    )


@pytest.fixture
def motion_request() -> MotionRequest:
    return MotionRequest(
        beta=ladder_plan(),
        problem=ladder_problem(),
        image=IMAGE,
        image_ref=LADDER_IMAGE,
        body=BodyModel.from_profile(profile_175()),
        px_per_cm=LADDER_PX_PER_CM,
    )


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    root = tmp_path / "prompts" / "greeter"
    root.mkdir(parents=True)
    (root / "v1.md").write_text(
        "---\nname: greeter\nversion: 1\nmodel: claude-haiku-5-5\neffort: low\nmax_tokens: 256\n---\n"
        "You greet climbers.\n=== user ===\nSay hi to $name.\n"
    )
    (root / "v2.md").write_text(
        "---\nname: greeter\nversion: 2\nmodel: claude-opus-5-5\neffort: high\nmax_tokens: 1024\n---\n"
        "You greet climbers warmly.\n=== user ===\nSay hi to $name on $wall.\n"
    )
    return tmp_path / "prompts"
