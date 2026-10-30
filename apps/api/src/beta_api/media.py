"""Local media store (normalised images, posters, videos) under ``var/media``."""

from __future__ import annotations

import os
import re
from pathlib import Path

from beta_core.errors import InvalidInputError, NotFoundError

_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$")


class LocalMediaStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, key: str) -> Path:
        if not _SAFE_KEY.match(key):
            raise InvalidInputError(f"invalid media key {key!r}")
        return self.root / key

    def put(self, key: str, data: bytes, content_type: str) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + f".tmp{os.getpid()}")
        tmp.write_bytes(data)
        tmp.replace(target)

    def get(self, key: str) -> bytes:
        target = self.path(key)
        if not target.is_file():
            raise NotFoundError("media", key)
        return target.read_bytes()

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()
