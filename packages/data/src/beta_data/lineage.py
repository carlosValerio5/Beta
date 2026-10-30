"""Run manifests: what each job read (with hashes), what it wrote, and with which code."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from beta_data import __version__
from beta_data.layout import Lakehouse


class InputRef(BaseModel):
    path: str
    sha256: str


class OutputRef(BaseModel):
    table: str
    path: str
    rows: int
    contract_version: int


class RunManifest(BaseModel):
    job: str
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    code_version: str
    inputs: list[InputRef] = Field(default_factory=list)
    outputs: list[OutputRef] = Field(default_factory=list)

    @classmethod
    def start(cls, job: str) -> RunManifest:
        now = datetime.now(UTC)
        return cls(
            job=job,
            run_id=now.strftime("%Y%m%dT%H%M%S%fZ"),
            started_at=now,
            code_version=code_version(),
        )

    def add_input(self, lake: Lakehouse, path: Path) -> None:
        self.inputs.append(
            InputRef(path=str(path.relative_to(lake.root)), sha256=sha256_file(path))
        )

    def add_output(self, lake: Lakehouse, table: str, path: Path, rows: int, version: int) -> None:
        self.outputs.append(
            OutputRef(
                table=table,
                path=str(path.relative_to(lake.root)),
                rows=rows,
                contract_version=version,
            )
        )

    def finish(self, lake: Lakehouse) -> RunManifest:
        self.finished_at = datetime.now(UTC)
        path = lake.manifests / self.job / f"{self.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return self


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_version() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return f"beta-data@{__version__}"
    return f"git:{sha}"
