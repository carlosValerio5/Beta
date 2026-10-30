"""Versioned prompt files: ``prompts/<name>/v<N>.md`` (see ``prompts/README.md``)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

USER_MARKER = "=== user ==="
_VERSION_FILE = re.compile(r"^v(\d+)\.md$")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    model: str
    effort: str
    max_tokens: int
    system: str
    user_template: str

    @property
    def ref(self) -> str:
        return f"{self.name}@v{self.version}"

    def render_user(self, **variables: object) -> str:
        try:
            return Template(self.user_template).substitute(
                **{k: str(v) for k, v in variables.items()}
            )
        except KeyError as exc:
            raise ValueError(f"missing prompt variable {exc} for {self.ref}") from exc


def parse_prompt(text: str) -> Prompt:
    if not text.startswith("---\n"):
        raise ValueError("prompt file must start with front matter")
    header, _, body = text[4:].partition("\n---\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.split("#", 1)[0].strip()
    system, marker, user = body.partition(USER_MARKER)
    if not marker:
        raise ValueError(f"prompt body must contain a {USER_MARKER!r} line")
    return Prompt(
        name=meta["name"],
        version=int(meta["version"]),
        model=meta["model"],
        effort=meta.get("effort", "high"),
        max_tokens=int(meta.get("max_tokens", "16000")),
        system=system.strip(),
        user_template=user.strip(),
    )


class PromptRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root

    def versions(self, name: str) -> list[int]:
        directory = self.root / name
        if not directory.is_dir():
            raise FileNotFoundError(f"no prompt named {name!r} under {self.root}")
        found = [int(m.group(1)) for p in directory.iterdir() if (m := _VERSION_FILE.match(p.name))]
        if not found:
            raise FileNotFoundError(f"prompt {name!r} has no versions")
        return sorted(found)

    def get(self, name: str, version: int | None = None) -> Prompt:
        chosen = version if version is not None else self.versions(name)[-1]
        path = self.root / name / f"v{chosen}.md"
        if not path.is_file():
            raise FileNotFoundError(f"prompt {name}@v{chosen} not found at {path}")
        prompt = parse_prompt(path.read_text(encoding="utf-8"))
        if (prompt.name, prompt.version) != (name, chosen):
            raise ValueError(f"{path} declares {prompt.ref}; expected {name}@v{chosen}")
        return prompt


def default_prompts_dir() -> Path:
    """``$BETA_PROMPTS_DIR``, else the nearest ``prompts/`` above the cwd or this file."""
    if env := os.environ.get("BETA_PROMPTS_DIR"):
        return Path(env)
    for start in (Path.cwd(), Path(__file__).resolve()):
        for parent in [start, *start.parents]:
            candidate = parent / "prompts"
            if (candidate / "beta_planner").is_dir():
                return candidate
    raise FileNotFoundError("could not locate the prompts/ directory; set BETA_PROMPTS_DIR")
