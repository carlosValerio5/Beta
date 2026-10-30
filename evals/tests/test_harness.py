from __future__ import annotations

import json
from pathlib import Path

from beta_evals.golden import load_cases, synthetic_cases
from beta_evals.harness import run_eval
from beta_llm.heuristic import ChoreographyDirector, HeuristicBetaPlanner
from beta_llm.planner import ClaudeBetaPlanner
from beta_llm.prompts import PromptRegistry, default_prompts_dir
from beta_llm.transport import ScriptedTransport
from beta_vision.synthetic import SyntheticWallGenerator


def test_synthetic_cases_have_truth() -> None:
    cases = synthetic_cases(2, start=100)
    assert [c.case_id for c in cases] == ["synthetic-100", "synthetic-101"]
    assert cases[0].truth_holds
    assert cases[0].truth.top_hold_id in {h.id for h in cases[0].truth_holds}


def test_load_cases_reads_the_gold_golden_set(tmp_path: Path) -> None:
    wall = SyntheticWallGenerator(5).generate()
    image = tmp_path / "silver" / "images" / "files" / "x.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(wall.image)
    golden = tmp_path / "gold" / "golden_set.jsonl"
    golden.parent.mkdir(parents=True)
    golden.write_text(
        json.dumps(
            {
                "analysis_id": "ana_x",
                "image_path": "silver/images/files/x.jpg",
                "px_per_cm": wall.px_per_cm,
                "truth_holds": [h.model_dump(mode="json") for h in wall.holds],
                "truth": {
                    "problem_color": wall.problem_color,
                    "start_hold_ids": list(wall.start_hold_ids),
                    "top_hold_id": wall.top_hold_id,
                    "foot_hold_ids": list(wall.foot_hold_ids),
                },
            }
        )
        + "\n"
    )
    cases = load_cases(tmp_path, limit=5)
    assert [c.case_id for c in cases] == ["ana_x"]
    assert cases[0].image == wall.image


def test_load_cases_falls_back_to_synthetic(tmp_path: Path) -> None:
    assert len(load_cases(tmp_path, limit=3)) == 3


def test_offline_pipeline_scores_well() -> None:
    report = run_eval(synthetic_cases(3, start=100), HeuristicBetaPlanner(), ChoreographyDirector())
    s = report.summary
    assert s["n_cases"] == 3
    assert s["beta_success_rate"] == 1.0
    assert s["spec_valid_rate"] == 1.0
    assert s["detection_recall_mean"] >= 0.9
    assert report.planner == HeuristicBetaPlanner.name


def test_adapter_failures_are_recorded_not_raised() -> None:
    broken = ClaudeBetaPlanner(
        ScriptedTransport("not json", "not json", "not json"), PromptRegistry(default_prompts_dir())
    )
    report = run_eval(synthetic_cases(1, start=100), broken, ChoreographyDirector())
    result = report.cases[0]
    assert result.beta_status == "failed"
    assert result.error
    assert report.summary["beta_success_rate"] == 0.0
