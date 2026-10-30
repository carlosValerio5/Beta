"""SQLite repositories: one table per aggregate, the aggregate stored as JSON (ADR-0003)."""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from beta_core.errors import NotFoundError

_TABLE = re.compile(r"^[a-z_]+$")


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall()
            self._conn.commit()
            return rows


class SqliteRepository[T: BaseModel]:
    def __init__(self, db: Database, table: str, model: type[T]) -> None:
        if not _TABLE.match(table):
            raise ValueError(f"invalid table name {table!r}")
        self._db = db
        self._table = table
        self._model = model
        db.execute(
            f"CREATE TABLE IF NOT EXISTS {table} ("
            "id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )

    def get(self, entity_id: str) -> T:
        rows = self._db.execute(f"SELECT payload FROM {self._table} WHERE id = ?", (entity_id,))
        if not rows:
            raise NotFoundError(self._table.removesuffix("s"), entity_id)
        return self._model.model_validate_json(rows[0][0])

    def save(self, entity: T) -> None:
        entity_id = entity.id  # type: ignore[attr-defined]
        self._db.execute(
            f"INSERT INTO {self._table} (id, payload) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = CURRENT_TIMESTAMP",
            (entity_id, entity.model_dump_json()),
        )

    def find(self, **where: object) -> list[T]:
        rows = self._db.execute(f"SELECT payload FROM {self._table} ORDER BY rowid")
        entities = [self._model.model_validate_json(r[0]) for r in rows]
        return [e for e in entities if all(getattr(e, k) == v for k, v in where.items())]
