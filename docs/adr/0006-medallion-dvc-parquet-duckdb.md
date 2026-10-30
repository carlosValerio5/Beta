# 0006 — Medallion data with DVC + Parquet + DuckDB

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Every photo, detection, beta, video spec and feedback event is future training and evaluation data.
We need reproducible snapshots without a data platform team.

## Decision
- **Bronze** (raw, append-only): uploaded images (content-addressed), JSONL domain events, raw LLM
  exchanges.
- **Silver** (clean, conformed): normalised deduplicated images; typed Parquet tables validated
  against versioned contracts.
- **Gold** (curated): marts, golden eval set, detector training export.
- Python jobs (`beta-data run …`) with DuckDB/PyArrow; each run writes a lineage manifest.
- **DVC** versions `data/` (local remote now, S3 later); `dvc.yaml` declares the stages.

## Consequences
- `git checkout <tag> && dvc checkout` reproduces any dataset version.
- No streaming; batch jobs run on demand or on a schedule.

## Alternatives considered
- *Delta Lake / Iceberg* — time travel is nice, but DVC already gives snapshots and fits git.
- *lakeFS* — a server to operate. *Dagster* — worth it once there are >10 assets; revisit then.
