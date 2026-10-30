from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa
import pytest
from pydantic import ValidationError

from beta_data.contracts import CONTRACTS, SilverImage, contract
from beta_data.layout import Lakehouse
from beta_data.tables import read_rows, write_table


def test_registry_has_every_layer_table() -> None:
    silver = {c.name for c in CONTRACTS if c.layer == "silver"}
    gold = {c.name for c in CONTRACTS if c.layer == "gold"}
    assert {
        "images",
        "holds",
        "problems",
        "betas",
        "moves",
        "motion_specs",
        "keyframes",
        "feedback",
        "renders",
    } <= silver
    assert {"beta_quality", "confusing_moves"} <= gold
    assert all(c.version >= 1 for c in CONTRACTS)


def test_arrow_schema_maps_types() -> None:
    schema = contract("images").arrow_schema()
    assert schema.field("width").type == pa.int64()
    assert schema.field("ingested_at").type == pa.timestamp("us", tz="UTC")
    assert schema.field("duplicate_of").nullable
    assert not schema.field("image_sha256").nullable
    assert contract("problems").arrow_schema().field("start_hold_ids").type == pa.list_(pa.int64())


def test_validation_rejects_bad_rows() -> None:
    with pytest.raises(ValidationError):
        contract("images").validate_rows([{"image_sha256": "x"}])


def test_write_and_read_roundtrip(lake: Lakehouse) -> None:
    row = SilverImage(
        image_sha256="b" * 64,
        source_sha256="a" * 64,
        analysis_id="ana_1",
        device_id="dev_1",
        width=10,
        height=20,
        dhash="0" * 16,
        gps_stripped=False,
        duplicate_of=None,
        ingested_at=datetime(2026, 10, 30, tzinfo=UTC),
    )
    path = write_table(lake, contract("images"), [row.model_dump()])
    assert path == lake.silver / "images" / "v1" / "part-0000.parquet"
    assert read_rows(lake, "images") == [row.model_dump()]
