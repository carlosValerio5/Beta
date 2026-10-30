from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from beta_data.cli import app

runner = CliRunner()


def test_seed_run_status(tmp_path: Path) -> None:
    root = str(tmp_path / "data")
    seeded = runner.invoke(app, ["seed", "--count", "1", "--root", root])
    assert seeded.exit_code == 0, seeded.output

    ran = runner.invoke(app, ["run", "all", "--root", root])
    assert ran.exit_code == 0, ran.output

    status = runner.invoke(app, ["status", "--root", root])
    assert status.exit_code == 0, status.output
    assert "silver/betas" in status.output
    assert "gold/beta_quality" in status.output


def test_unknown_job(tmp_path: Path) -> None:
    result = runner.invoke(app, ["run", "nope", "--root", str(tmp_path)])
    assert result.exit_code != 0
