"""Pure metric functions. The harness only wires them up."""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from beta_core.domain.holds import Hold
from beta_vision.detect import match_holds

MATCH_DISTANCE_PX = 15.0


class DetectionScores(BaseModel):
    precision: float
    recall: float
    color_accuracy: float


def detection_scores(
    truth: Sequence[Hold], found: Sequence[Hold], max_distance: float = MATCH_DISTANCE_PX
) -> DetectionScores:
    if not truth and not found:
        return DetectionScores(precision=1.0, recall=1.0, color_accuracy=1.0)
    matches = match_holds(truth, found, max_distance)
    correct = sum(1 for t, f in matches if t.color == f.color)
    return DetectionScores(
        precision=len(matches) / len(found) if found else 0.0,
        recall=len(matches) / len(truth) if truth else 1.0,
        color_accuracy=correct / len(matches) if matches else 0.0,
    )


class CaseResult(BaseModel):
    case_id: str
    detection_precision: float
    detection_recall: float
    color_accuracy: float
    problem_mapped: bool
    beta_status: str
    beta_attempts: int
    n_moves: int
    spec_valid: bool
    beta_latency_s: float | None
    video_latency_s: float | None
    error: str | None


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def summarise(results: Sequence[CaseResult]) -> dict[str, float]:
    n = len(results)
    ready = [r for r in results if r.beta_status == "ready"]
    attempted = [r for r in results if r.beta_attempts > 0]
    latencies = [r.beta_latency_s for r in results if r.beta_latency_s is not None]
    return {
        "n_cases": float(n),
        "detection_precision_mean": _mean([r.detection_precision for r in results]),
        "detection_recall_mean": _mean([r.detection_recall for r in results]),
        "color_accuracy_mean": _mean([r.color_accuracy for r in results]),
        "problem_mapped_rate": sum(r.problem_mapped for r in results) / n if n else 0.0,
        "beta_success_rate": len(ready) / n if n else 0.0,
        "first_try_rate": sum(1 for r in ready if r.beta_attempts == 1) / n if n else 0.0,
        "mean_repairs": _mean([max(r.beta_attempts - 1, 0) for r in attempted]),
        "spec_valid_rate": sum(r.spec_valid for r in results) / n if n else 0.0,
        "mean_moves": _mean([r.n_moves for r in ready]),
        "p50_beta_latency_s": statistics.median(latencies) if latencies else 0.0,
    }


def check_thresholds(summary: Mapping[str, float], thresholds: Mapping[str, float]) -> list[str]:
    failures = []
    for metric, minimum in thresholds.items():
        actual = summary.get(metric)
        if actual is None or actual < minimum:
            shown = "missing" if actual is None else f"{actual:.3f}"
            failures.append(f"{metric} {shown} < {minimum:.3f}")
    return failures
