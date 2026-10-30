# beta_data — agent notes

The medallion lakehouse. See [`docs/data/medallion.md`](../../docs/data/medallion.md).

| Module | Does |
|---|---|
| `layout.py` | `Lakehouse`: every path under `data/` is computed here, nowhere else |
| `bronze.py` | `BronzeWriter`: append-only raw images + JSONL events (implements `EventSink`, `RawImageSink`) |
| `contracts.py` | Versioned silver/gold table contracts (Pydantic row model + Arrow schema) |
| `lineage.py` | Run manifests: inputs (sha256), outputs, row counts, code version |
| `jobs/bronze_to_silver.py` | Normalise + dedupe images; explode events into silver tables |
| `jobs/silver_to_gold.py` | Marts, golden set, detector training export |
| `seed.py` | Synthetic walls into bronze (with ground-truth events) |
| `cli.py` | `beta-data seed | ingest | run <job>` |

Rules:
- Bronze is append-only and immutable. Jobs never write to bronze.
- Every silver/gold write validates against its contract and emits a lineage manifest.
- Jobs are idempotent: rerunning on the same bronze produces byte-identical tables.
- Changing a contract's columns = new contract version + doc update in `docs/data/contracts.md`.
