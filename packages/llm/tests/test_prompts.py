from __future__ import annotations

from pathlib import Path

import pytest

from beta_llm.prompts import PromptRegistry


def test_latest_version_by_default(prompts_dir: Path) -> None:
    prompt = PromptRegistry(prompts_dir).get("greeter")
    assert prompt.version == 2
    assert prompt.ref == "greeter@v2"
    assert prompt.model == "claude-opus-5-5"
    assert prompt.effort == "high"
    assert prompt.max_tokens == 1024
    assert prompt.system == "You greet climbers warmly."


def test_pinned_version(prompts_dir: Path) -> None:
    prompt = PromptRegistry(prompts_dir).get("greeter", version=1)
    assert prompt.render_user(name="Maya") == "Say hi to Maya."


def test_missing_variable_is_an_error(prompts_dir: Path) -> None:
    prompt = PromptRegistry(prompts_dir).get("greeter")
    with pytest.raises(ValueError, match="wall"):
        prompt.render_user(name="Maya")


def test_unknown_prompt(prompts_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PromptRegistry(prompts_dir).get("nope")


@pytest.mark.parametrize("name", ["beta_planner", "motion_director", "hold_classifier"])
def test_repo_prompts_load(registry: PromptRegistry, name: str) -> None:
    prompt = registry.get(name)
    assert prompt.model.startswith("claude-")
    assert prompt.system
    assert "$" in prompt.user_template
