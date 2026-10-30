"""Read/write contract-validated Parquet tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from beta_data.contracts import TableContract, contract
from beta_data.layout import Lakehouse

PART = "part-0000.parquet"


def table_path(lake: Lakehouse, c: TableContract) -> Path:
    return lake.table_dir(c.layer, c.name, c.version) / PART


def write_table(lake: Lakehouse, c: TableContract, rows: Iterable[Mapping[str, Any]]) -> Path:
    """Validate, sort and (re)write the whole table — jobs are full refreshes, so reruns converge."""
    validated = c.validate_rows(rows)
    if c.sort_by:
        validated.sort(key=lambda r: tuple((r[k] is None, r[k]) for k in c.sort_by))
    table = pa.Table.from_pylist(validated, schema=c.arrow_schema())
    path = table_path(lake, c)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(path)
    return path


def read_rows(lake: Lakehouse, name: str, layer: str = "silver") -> list[dict[str, Any]]:
    c = contract(name)
    if c.layer != layer:
        raise KeyError(f"{name} is a {c.layer} table, not {layer}")
    path = table_path(lake, c)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = pq.read_table(path).to_pylist()
    return rows
