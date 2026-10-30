from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from beta_evals.cli import app

runner = CliRunner()


def test_offline_run_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "report"
    result = runner.invoke(
        app,
        [
            "run",
            "--offline",
            "--cases",
            "2",
            "--out",
            str(out),
            "--data-root",
            str(tmp_path / "none"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads((out.with_suffix(".json")).read_text())
    assert report["summary"]["n_cases"] == 2
    assert out.with_suffix(".md").read_text().startswith("# Eval report")
    assert "beta_success_rate" in result.output


def test_thresholds_gate_the_exit_code(tmp_path: Path) -> None:
    thresholds = tmp_path / "t.json"
    thresholds.write_text(json.dumps({"beta_success_rate": 1.01}))
    result = runner.invoke(
        app,
        [
            "run",
            "--offline",
            "--cases",
            "1",
            "--out",
            str(tmp_path / "r"),
            "--thresholds",
            str(thresholds),
            "--data-root",
            str(tmp_path / "none"),
        ],
    )
    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_live_requires_an_api_key(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["run", "--live", "--cases", "1", "--out", str(tmp_path / "r")])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output
