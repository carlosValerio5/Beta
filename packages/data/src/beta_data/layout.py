"""Every path under ``data/`` is computed here (see docs/data/medallion.md)."""

from __future__ import annotations

from datetime import date
from pathlib import Path


class Lakehouse:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    @property
    def bronze(self) -> Path:
        return self.root / "bronze"

    @property
    def silver(self) -> Path:
        return self.root / "silver"

    @property
    def gold(self) -> Path:
        return self.root / "gold"

    @property
    def manifests(self) -> Path:
        return self.root / "_manifests"

    # ---------------------------------------------------------------- bronze

    @staticmethod
    def bronze_image_key(sha256: str, ext: str) -> str:
        """Content-addressed, sharded by the first two hex characters."""
        return f"bronze/images/{sha256[:2]}/{sha256}.{ext}"

    def events_file(self, day: date) -> Path:
        return self.bronze / "events" / f"date={day.isoformat()}" / "events.jsonl"

    def ground_truth_path(self, raw_sha256: str) -> Path:
        return self.bronze / "ground_truth" / f"{raw_sha256}.json"

    # ---------------------------------------------------------------- silver / gold

    def table_dir(self, layer: str, name: str, version: int) -> Path:
        base = self.silver if layer == "silver" else self.gold
        return base / name / f"v{version}"

    def silver_image(self, sha256: str) -> Path:
        return self.silver / "images" / "files" / f"{sha256}.jpg"
