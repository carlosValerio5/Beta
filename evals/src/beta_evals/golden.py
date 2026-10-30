"""Golden evaluation cases: the gold layer's golden set when present, synthetic walls otherwise."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from beta_core.domain.holds import Hold
from beta_vision.synthetic import SyntheticWallGenerator

#: Synthetic eval walls use seeds disjoint from `beta-data seed` (0..) to avoid testing on seeds.
SYNTHETIC_START = 100


class Truth(BaseModel):
    problem_color: str
    start_hold_ids: list[int]
    top_hold_id: int
    foot_hold_ids: list[int] = Field(default_factory=list)


class GoldenCase(BaseModel):
    case_id: str
    image: bytes
    px_per_cm: float
    truth_holds: list[Hold]
    truth: Truth


def synthetic_cases(n: int, start: int = SYNTHETIC_START) -> list[GoldenCase]:
    cases = []
    for seed in range(start, start + n):
        wall = SyntheticWallGenerator(seed).generate()
        cases.append(
            GoldenCase(
                case_id=f"synthetic-{seed}",
                image=wall.image,
                px_per_cm=wall.px_per_cm,
                truth_holds=list(wall.holds),
                truth=Truth(
                    problem_color=wall.problem_color,
                    start_hold_ids=list(wall.start_hold_ids),
                    top_hold_id=wall.top_hold_id,
                    foot_hold_ids=list(wall.foot_hold_ids),
                ),
            )
        )
    return cases


def load_cases(data_root: Path, limit: int) -> list[GoldenCase]:
    """Cases from ``<data_root>/gold/golden_set.jsonl`` (see docs/data/contracts.md), else synthetic."""
    golden = data_root / "gold" / "golden_set.jsonl"
    if not golden.is_file():
        return synthetic_cases(limit)
    cases = []
    for line in golden.read_text(encoding="utf-8").splitlines()[:limit]:
        row = json.loads(line)
        cases.append(
            GoldenCase(
                case_id=row["analysis_id"],
                image=(data_root / row["image_path"]).read_bytes(),
                px_per_cm=row["px_per_cm"],
                truth_holds=[Hold.model_validate(h) for h in row["truth_holds"]],
                truth=Truth.model_validate(row["truth"]),
            )
        )
    return cases
