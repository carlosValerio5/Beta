"""``beta-eval run``: score the generation pipeline and gate on thresholds.

Modes:
  --offline (default)   heuristic planner + director; deterministic, free, CI-safe
  --cassettes DIR       Claude adapters replaying recorded responses (no network)
  --live                Claude adapters against the API (needs ANTHROPIC_API_KEY; spends credit);
                        with --cassettes DIR it also records responses for later replay
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import typer

from beta_core.ports import BetaPlanner, MotionDirector
from beta_evals.golden import load_cases
from beta_evals.harness import EvalReport, run_eval
from beta_evals.metrics import check_thresholds
from beta_llm.director import ClaudeMotionDirector
from beta_llm.heuristic import ChoreographyDirector, HeuristicBetaPlanner
from beta_llm.planner import ClaudeBetaPlanner
from beta_llm.prompts import PromptRegistry, default_prompts_dir
from beta_llm.transport import AnthropicTransport, CassetteTransport, Transport

app = typer.Typer(no_args_is_help=True, help="Beta Climbing evaluation harness.")


@app.callback()
def main() -> None:
    """Evaluate detection, beta planning and motion direction on the golden set."""


def _adapters(live: bool, cassettes: Path | None) -> tuple[BetaPlanner, MotionDirector]:
    transport: Transport | None = None
    if live:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            typer.echo("ANTHROPIC_API_KEY is required for --live")
            raise typer.Exit(2)
        transport = AnthropicTransport.from_api_key(key)
        if cassettes:
            transport = CassetteTransport(cassettes, inner=transport)
    elif cassettes:
        transport = CassetteTransport(cassettes)
    if transport is None:
        return HeuristicBetaPlanner(), ChoreographyDirector()
    registry = PromptRegistry(default_prompts_dir())
    return ClaudeBetaPlanner(transport, registry), ClaudeMotionDirector(transport, registry)


def _markdown(report: EvalReport) -> str:
    lines = [
        "# Eval report",
        "",
        f"- **When:** {report.created_at.isoformat()}",
        f"- **Planner:** `{report.planner}`  **Director:** `{report.director}`",
        f"- **Result:** {'FAILED — ' + '; '.join(report.failures) if report.failures else 'passed'}",
        "",
        "| Metric | Value | Threshold |",
        "|---|---|---|",
    ]
    for metric, value in report.summary.items():
        threshold = report.thresholds.get(metric)
        lines.append(
            f"| {metric} | {value:.3f} | {'' if threshold is None else f'≥ {threshold}'} |"
        )
    lines += [
        "",
        "| Case | Recall | Precision | Beta | Attempts | Moves | Spec | Error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in report.cases:
        lines.append(
            f"| {c.case_id} | {c.detection_recall:.2f} | {c.detection_precision:.2f} | {c.beta_status} | "
            f"{c.beta_attempts} | {c.n_moves} | {'✓' if c.spec_valid else '✗'} | {c.error or ''} |"
        )
    return "\n".join(lines) + "\n"


@app.command()
def run(
    offline: bool = typer.Option(False, "--offline", help="Force offline heuristics."),
    live: bool = typer.Option(False, "--live", help="Call Claude (also enabled by BETA_LIVE=1)."),
    cases: int = typer.Option(12, help="Maximum number of golden cases."),
    out: Path | None = typer.Option(None, help="Report path without extension."),
    data_root: Path = typer.Option(
        Path("data"), help="Lakehouse root holding gold/golden_set.jsonl."
    ),
    thresholds: Path = typer.Option(Path("evals/thresholds.json"), help="Minimum metric values."),
    cassettes: Path | None = typer.Option(
        None, help="Record/replay directory for Claude responses."
    ),
) -> None:
    """Run the eval, write JSON + Markdown reports, exit 1 if a threshold fails."""
    use_live = (live or os.environ.get("BETA_LIVE") == "1") and not offline
    planner, director = _adapters(use_live, cassettes)
    report = run_eval(load_cases(data_root, cases), planner, director)
    limits: dict[str, float] = json.loads(thresholds.read_text()) if thresholds.is_file() else {}
    report = report.model_copy(
        update={"thresholds": limits, "failures": check_thresholds(report.summary, limits)}
    )

    target = out or Path("evals/reports") / f"eval-{datetime.now(UTC):%Y%m%dT%H%M%S}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.with_suffix(".json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    target.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")

    typer.echo(f"planner={report.planner} director={report.director} cases={len(report.cases)}")
    for metric, value in report.summary.items():
        typer.echo(f"  {metric:<26} {value:8.3f}")
    typer.echo(f"report: {target.with_suffix('.md')}")
    if report.failures:
        typer.echo("FAILED: " + "; ".join(report.failures))
        raise typer.Exit(1)
    typer.echo("PASSED")
