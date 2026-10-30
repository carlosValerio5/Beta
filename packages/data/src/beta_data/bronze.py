"""The only way into bronze: raw images, domain events, synthetic ground truth. Append-only."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from datetime import UTC
from pathlib import Path
from typing import Any

from beta_core.domain.events import DomainEvent
from beta_core.ports import SanitizedUpload
from beta_data.layout import Lakehouse

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _write_once(path: Path, data: bytes) -> None:
    """Atomically create ``path``; never overwrite (bronze is immutable)."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    tmp.write_bytes(data)
    tmp.replace(path)


class BronzeWriter:
    """Implements the ``RawImageSink`` and ``EventSink`` ports on top of the lakehouse."""

    def __init__(self, lake: Lakehouse) -> None:
        self.lake = lake
        self._lock = threading.Lock()

    def store_raw(self, upload: SanitizedUpload) -> str:
        key = self.lake.bronze_image_key(upload.sha256, EXTENSIONS.get(upload.content_type, "bin"))
        _write_once(self.lake.root / key, upload.data)
        return key

    def emit(self, event: DomainEvent) -> None:
        path = self.lake.events_file(event.occurred_at.astimezone(UTC).date())
        line = event.model_dump_json() + "\n"
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    def store_ground_truth(self, raw_sha256: str, truth: dict[str, Any]) -> Path:
        path = self.lake.ground_truth_path(raw_sha256)
        _write_once(path, (json.dumps(truth, indent=2, sort_keys=True) + "\n").encode())
        return path


def event_files(lake: Lakehouse) -> list[Path]:
    return sorted(lake.bronze.glob("events/date=*/events.jsonl"))


def read_events(lake: Lakehouse) -> Iterator[DomainEvent]:
    """All bronze events, partition by partition, in the order they were appended."""
    for path in event_files(lake):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield DomainEvent.model_validate_json(line)
