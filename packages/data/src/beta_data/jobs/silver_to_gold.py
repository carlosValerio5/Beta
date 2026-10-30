"""Silver → gold: quality marts (DuckDB), the golden eval set and a COCO detector export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from beta_data.contracts import CONTRACTS, contract
from beta_data.layout import Lakehouse
from beta_data.lineage import RunManifest
from beta_data.tables import read_rows, table_path, write_table

JOB = "silver_to_gold"

BETA_QUALITY_SQL = """
WITH per_beta AS (
    SELECT b.beta_id,
           coalesce(b.planner, 'unknown') AS planner,
           bool_or(f.kind = 'sent') AS sent,
           bool_or(f.kind = 'useful') AS useful,
           bool_or(f.kind = 'not_useful') AS not_useful,
           count(*) FILTER (WHERE f.kind = 'move_looks_wrong') AS looks_wrong
    FROM betas b LEFT JOIN feedback f USING (beta_id)
    WHERE b.status = 'ready'
    GROUP BY 1, 2
)
SELECT planner,
       count(*)::BIGINT AS n_betas,
       (count(*) FILTER (WHERE sent))::BIGINT AS n_sent,
       (count(*) FILTER (WHERE useful))::BIGINT AS n_useful,
       (count(*) FILTER (WHERE not_useful))::BIGINT AS n_not_useful,
       sum(looks_wrong)::BIGINT AS n_looks_wrong,
       (count(*) FILTER (WHERE sent OR useful))::DOUBLE / count(*) AS useful_rate
FROM per_beta
GROUP BY planner
ORDER BY planner
"""

CONFUSING_MOVES_SQL = """
WITH per_move AS (
    SELECT f.beta_id, f.move_index, m.technique, m.limb,
           (count(*) FILTER (WHERE f.kind = 'rewatch'))::BIGINT AS rewatches,
           (count(*) FILTER (WHERE f.kind = 'move_looks_wrong'))::BIGINT AS looks_wrong
    FROM feedback f
    JOIN moves m ON m.beta_id = f.beta_id AND m.move_index = f.move_index
    WHERE f.move_index IS NOT NULL
    GROUP BY 1, 2, 3, 4
)
SELECT *, (3 * looks_wrong + rewatches)::BIGINT AS score
FROM per_move
ORDER BY score DESC, beta_id, move_index
"""


def run(lake: Lakehouse) -> RunManifest:
    manifest = RunManifest.start(JOB)
    con = duckdb.connect()
    for c in CONTRACTS:
        if c.layer != "silver":
            continue
        path = table_path(lake, c)
        if not path.exists():
            raise FileNotFoundError(f"silver table {c.name} missing; run bronze-to-silver first")
        manifest.add_input(lake, path)
        con.execute(f"CREATE VIEW {c.name} AS SELECT * FROM read_parquet('{path.as_posix()}')")

    for name, sql in (("beta_quality", BETA_QUALITY_SQL), ("confusing_moves", CONFUSING_MOVES_SQL)):
        rows = _query(con, sql)
        c = contract(name)
        out = write_table(lake, c, rows)
        manifest.add_output(lake, name, out, len(rows), c.version)

    cases = _golden_cases(lake)
    golden = lake.gold / "golden_set.jsonl"
    golden.parent.mkdir(parents=True, exist_ok=True)
    golden.write_text(
        "".join(json.dumps(c, sort_keys=True, default=str) + "\n" for c in cases), encoding="utf-8"
    )
    manifest.add_output(lake, "golden_set", golden, len(cases), 1)

    coco_path, n_images = _coco_export(lake, cases)
    manifest.add_output(lake, "detector_training", coco_path, n_images, 1)
    return manifest.finish(lake)


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    rel = con.sql(sql)
    columns = rel.columns
    return [dict(zip(columns, row, strict=True)) for row in rel.fetchall()]


def _golden_cases(lake: Lakehouse) -> list[dict[str, Any]]:
    """One case per image with ground truth and a selected problem (synthetic walls in v0)."""
    problems = {p["analysis_id"]: p for p in read_rows(lake, "problems")}
    holds_by_analysis: dict[str, list[dict[str, Any]]] = {}
    for h in read_rows(lake, "holds"):
        holds_by_analysis.setdefault(h["analysis_id"], []).append(h)
    positive = _positive_betas(lake)
    moves_by_beta: dict[str, list[dict[str, Any]]] = {}
    for m in read_rows(lake, "moves"):
        moves_by_beta.setdefault(m["beta_id"], []).append(m)

    cases = []
    for image in read_rows(lake, "images"):
        truth_path = lake.ground_truth_path(image["source_sha256"])
        problem = problems.get(image["analysis_id"])
        if image["duplicate_of"] or not truth_path.exists() or problem is None:
            continue
        truth = json.loads(truth_path.read_text())
        accepted = positive.get(image["analysis_id"])
        cases.append(
            {
                "analysis_id": image["analysis_id"],
                "image_sha256": image["image_sha256"],
                "image_path": str(lake.silver_image(image["image_sha256"]).relative_to(lake.root)),
                "width": image["width"],
                "height": image["height"],
                "px_per_cm": truth["px_per_cm"],
                "problem": problem,
                "holds": holds_by_analysis.get(image["analysis_id"], []),
                "truth_holds": truth["holds"],
                "truth": {
                    k: truth[k]
                    for k in ("problem_color", "start_hold_ids", "top_hold_id", "foot_hold_ids")
                },
                "accepted_beta": moves_by_beta.get(accepted) if accepted else None,
            }
        )
    return cases


def _positive_betas(lake: Lakehouse) -> dict[str, str]:
    """analysis_id → a beta the climber sent or found useful and never flagged."""
    feedback = read_rows(lake, "feedback")
    good = {f["beta_id"] for f in feedback if f["kind"] in ("sent", "useful")}
    bad = {f["beta_id"] for f in feedback if f["kind"] in ("move_looks_wrong", "not_useful")}
    return {
        b["analysis_id"]: b["beta_id"]
        for b in read_rows(lake, "betas")
        if b["status"] == "ready" and b["beta_id"] in good - bad
    }


def _coco_export(lake: Lakehouse, cases: list[dict[str, Any]]) -> tuple[Path, int]:
    colors = sorted({h["color"] for c in cases for h in c["truth_holds"]})
    category = {name: i + 1 for i, name in enumerate(colors)}
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    for image_id, case in enumerate(cases, start=1):
        images.append(
            {
                "id": image_id,
                "file_name": case["image_path"],
                "width": case["width"],
                "height": case["height"],
            }
        )
        for h in case["truth_holds"]:
            box = h["bbox"]
            annotations.append(
                {
                    "id": len(annotations) + 1,
                    "image_id": image_id,
                    "category_id": category[h["color"]],
                    "bbox": [box["x"], box["y"], box["w"], box["h"]],
                    "area": box["w"] * box["h"],
                    "iscrowd": 0,
                }
            )
    coco = {
        "info": {"description": "Beta hold detection (synthetic walls, v0)"},
        "images": images,
        "annotations": annotations,
        "categories": [{"id": i, "name": n, "supercategory": "hold"} for n, i in category.items()],
    }
    path = lake.gold / "detector_training" / "coco.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(coco, indent=1), encoding="utf-8")
    return path, len(images)
