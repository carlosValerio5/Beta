from __future__ import annotations

import io
import json

from PIL import Image

from beta_data.bronze import BronzeWriter
from beta_data.jobs import bronze_to_silver, silver_to_gold
from beta_data.layout import Lakehouse
from beta_data.tables import read_rows
from beta_vision.preprocess import PillowPreprocessor


def test_bronze_to_silver_builds_every_table(seeded: Lakehouse) -> None:
    manifest = bronze_to_silver.run(seeded)
    counts = {o.table: o.rows for o in manifest.outputs}
    assert counts["images"] == 3
    assert counts["holds"] > 3 * 10
    assert counts["problems"] == 3
    assert counts["betas"] == 3
    assert counts["moves"] >= 3 * 5
    assert counts["motion_specs"] == 3
    assert counts["keyframes"] == counts["moves"] + 3
    assert counts["feedback"] >= 3


def test_silver_images_are_normalised_without_exif(seeded: Lakehouse) -> None:
    bronze_to_silver.run(seeded)
    for row in read_rows(seeded, "images"):
        path = seeded.silver_image(row["image_sha256"])
        img = Image.open(io.BytesIO(path.read_bytes()))
        assert img.format == "JPEG"
        assert not img.getexif()


def test_bronze_to_silver_is_idempotent(seeded: Lakehouse) -> None:
    bronze_to_silver.run(seeded)
    first = {t: read_rows(seeded, t) for t in ("images", "betas", "moves", "keyframes")}
    bronze_to_silver.run(seeded)
    second = {t: read_rows(seeded, t) for t in ("images", "betas", "moves", "keyframes")}
    assert first == second


def test_duplicate_uploads_are_flagged(seeded: Lakehouse) -> None:
    from beta_data.ingest import ingest_bytes

    raw = next((seeded.bronze / "images").rglob("*.jpg")).read_bytes()
    ingest_bytes(seeded, raw + b"\x00", device_id="dev_dup")  # same pixels, different bytes
    bronze_to_silver.run(seeded)
    rows = read_rows(seeded, "images")
    assert sum(1 for r in rows if r["duplicate_of"] is not None) == 1


def test_manifest_records_lineage(seeded: Lakehouse) -> None:
    manifest = bronze_to_silver.run(seeded)
    path = seeded.manifests / "bronze_to_silver" / f"{manifest.run_id}.json"
    data = json.loads(path.read_text())
    assert data["job"] == "bronze_to_silver"
    assert all(len(i["sha256"]) == 64 for i in data["inputs"])
    assert {o["table"] for o in data["outputs"]} >= {"images", "betas"}
    assert all(o["contract_version"] >= 1 for o in data["outputs"])


def test_silver_to_gold_marts(seeded: Lakehouse) -> None:
    bronze_to_silver.run(seeded)
    manifest = silver_to_gold.run(seeded)
    outputs = {o.table for o in manifest.outputs}
    assert {"beta_quality", "confusing_moves", "golden_set", "detector_training"} <= outputs

    quality = read_rows(seeded, "beta_quality", layer="gold")
    assert sum(r["n_betas"] for r in quality) == 3
    assert all(0 <= r["useful_rate"] <= 1 for r in quality)

    confusing = read_rows(seeded, "confusing_moves", layer="gold")
    scores = [r["score"] for r in confusing]
    assert scores == sorted(scores, reverse=True)


def test_detector_training_is_valid_coco(seeded: Lakehouse) -> None:
    bronze_to_silver.run(seeded)
    silver_to_gold.run(seeded)
    coco = json.loads((seeded.gold / "detector_training" / "coco.json").read_text())
    image_ids = {i["id"] for i in coco["images"]}
    assert len(image_ids) == 3
    assert coco["annotations"]
    assert all(a["image_id"] in image_ids and len(a["bbox"]) == 4 for a in coco["annotations"])
    assert {c["name"] for c in coco["categories"]} >= {"yellow"}


def test_golden_set_lines_are_complete(seeded: Lakehouse) -> None:
    bronze_to_silver.run(seeded)
    silver_to_gold.run(seeded)
    lines = (seeded.gold / "golden_set.jsonl").read_text().splitlines()
    assert lines
    case = json.loads(lines[0])
    assert {"image_sha256", "image_path", "problem", "holds", "px_per_cm", "truth_holds"} <= set(case)


def test_ingest_strips_gps(lake: Lakehouse) -> None:
    from beta_data.ingest import ingest_bytes
    from beta_vision.preprocess import GPS_IFD

    exif = Image.Exif()
    exif[GPS_IFD] = {1: "N"}
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, format="JPEG", exif=exif)
    key = ingest_bytes(lake, buf.getvalue(), device_id="dev_1")
    stored = Image.open(io.BytesIO((lake.root / key).read_bytes()))
    assert not stored.getexif().get_ifd(GPS_IFD)
    assert BronzeWriter  # bronze writer is the only path in
    assert PillowPreprocessor
