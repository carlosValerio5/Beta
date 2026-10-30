from __future__ import annotations

import pytest

from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold
from beta_evals.metrics import (
    CaseResult,
    check_thresholds,
    detection_scores,
    summarise,
)


def hold(i: int, x: float, y: float, color: str = "yellow") -> Hold:
    return Hold(id=i, bbox=BBox(x=x - 10, y=y - 10, w=20, h=20), color=color)


def test_detection_scores_perfect() -> None:
    truth = [hold(0, 10, 10), hold(1, 100, 100)]
    scores = detection_scores(truth, truth)
    assert scores.precision == scores.recall == scores.color_accuracy == 1.0


def test_detection_scores_partial() -> None:
    truth = [hold(0, 10, 10), hold(1, 100, 100)]
    found = [hold(5, 12, 11, color="red"), hold(6, 500, 500)]
    scores = detection_scores(truth, found)
    assert scores.recall == 0.5
    assert scores.precision == 0.5
    assert scores.color_accuracy == 0.0


def test_detection_scores_empty() -> None:
    scores = detection_scores([], [])
    assert scores.recall == 1.0
    assert scores.precision == 1.0


def case(**kw: object) -> CaseResult:
    base = {
        "case_id": "c",
        "detection_precision": 1.0,
        "detection_recall": 1.0,
        "color_accuracy": 1.0,
        "problem_mapped": True,
        "beta_status": "ready",
        "beta_attempts": 1,
        "n_moves": 10,
        "spec_valid": True,
        "beta_latency_s": 0.1,
        "video_latency_s": 0.1,
        "error": None,
    }
    return CaseResult.model_validate(base | kw)


def test_summarise_rates_and_means() -> None:
    summary = summarise(
        [
            case(),
            case(beta_status="failed", beta_attempts=3, spec_valid=False, n_moves=0),
            case(beta_attempts=2),
        ]
    )
    assert summary["n_cases"] == 3
    assert summary["beta_success_rate"] == pytest.approx(2 / 3)
    assert summary["first_try_rate"] == pytest.approx(1 / 3)
    assert summary["mean_repairs"] == pytest.approx(1.0)
    assert summary["spec_valid_rate"] == pytest.approx(2 / 3)


def test_thresholds() -> None:
    summary = {"beta_success_rate": 0.8, "detection_recall_mean": 0.95}
    failures = check_thresholds(summary, {"beta_success_rate": 0.9, "detection_recall_mean": 0.9})
    assert failures == ["beta_success_rate 0.800 < 0.900"]
    assert check_thresholds(summary, {"detection_recall_mean": 0.9}) == []
