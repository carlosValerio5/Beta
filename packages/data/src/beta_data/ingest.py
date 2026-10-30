"""Add photos to bronze outside the app (e.g. a folder of consented gym photos)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from beta_core.domain.events import DomainEvent, EventName
from beta_core.ports import ImagePreprocessor
from beta_data.bronze import BronzeWriter
from beta_data.layout import Lakehouse
from beta_vision.preprocess import PillowPreprocessor


def ingest_bytes(
    lake: Lakehouse,
    raw: bytes,
    *,
    device_id: str,
    preprocessor: ImagePreprocessor | None = None,
) -> str:
    """Sanitise (strip GPS), store raw, emit ``image.ingested``. Returns the bronze key."""
    upload = (preprocessor or PillowPreprocessor()).sanitize(raw)
    writer = BronzeWriter(lake)
    key = writer.store_raw(upload)
    writer.emit(
        DomainEvent(
            name=EventName.IMAGE_INGESTED,
            occurred_at=datetime.now(UTC),
            entity_id=f"raw_{upload.sha256[:16]}",
            payload={
                "device_id": device_id,
                "raw_key": key,
                "raw_sha256": upload.sha256,
                "content_type": upload.content_type,
                "gps_stripped": upload.gps_stripped,
                "image": None,
                "wall_height_cm": None,
                "source": "ingest",
            },
        )
    )
    return key


def ingest_paths(lake: Lakehouse, paths: Iterable[Path], device_id: str = "ingest") -> list[str]:
    return [ingest_bytes(lake, p.read_bytes(), device_id=device_id) for p in paths]
