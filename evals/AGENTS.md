# beta_evals — agent notes

Runs the full generation pipeline (detect → plan → validate → direct → validate) over the golden
set and scores it. CI runs it offline; `make eval-live` runs it against Claude.

| Module | Does |
|---|---|
| `golden.py` | Loads golden cases (gold layer if present, else seeded synthetic walls) |
| `metrics.py` | Pure metric functions (detection P/R, validity, reach feasibility, repairs, latency) |
| `harness.py` | Runs cases through the pipeline and aggregates a `EvalReport` |
| `cli.py` | `beta-eval run [--offline] [--cases N] [--out PATH]` with threshold gate |

Rules:
- Metrics are pure functions with unit tests. The harness only wires them up.
- Thresholds live in `evals/thresholds.json`; lowering one needs a written reason in the PR.
- Never run live evals unprompted — they spend API credit.
