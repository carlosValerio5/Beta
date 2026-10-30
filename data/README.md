# data/

Medallion lakehouse. Contents are **not** in git — they are versioned with DVC
(see [docs/data/medallion.md](../docs/data/medallion.md)).

```
data/
├── bronze/      raw, append-only (images/, events/, llm/)
├── silver/      cleaned, typed Parquet + normalised images
├── gold/        marts, golden_set, detector_training
└── _manifests/  lineage manifests per job run
```

Only `beta_data` writes here. Never edit bronze by hand.

## External datasets

| Dataset | License | Used in | Notes |
|---|---|---|---|
| *(none yet — v0 uses synthetic walls only)* | | | |
