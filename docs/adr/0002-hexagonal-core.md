# 0002 — Hexagonal (ports & adapters) core

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Every external piece of this system is expected to change: the hold detector (colour → YOLO), the
LLM (model versions, prompts), storage (SQLite → Postgres, local → S3), the renderer. The domain
rules — what a valid beta is, what a reachable move is — should not.

## Decision
`beta_core` holds the domain model, validators, kinematics, **ports** (Python `Protocol`s) and
**use cases**. It depends only on Pydantic. Adapters live in other packages and implement ports.
`apps/api` is the composition root that wires adapters to use cases.

SOLID mapping:
- **S** — one use case per class (`AnalyzeBoulder`, `GenerateBeta`, `GenerateVideo`, …).
- **O** — new detectors/planners/renderers are new adapters; core is untouched.
- **L** — shared contract tests run against every adapter of a port, fakes included.
- **I** — small ports (`HoldDetector`, `BetaPlanner`, `MotionDirector`, `VideoRenderer`, `EventSink`, …).
- **D** — use cases receive ports through their constructors.

## Consequences
- Core tests are fast and need no network, GPU or disk.
- Some duplication of DTOs at the HTTP edge (wire schemas vs domain models) — accepted for a stable API.
- Ruff `banned-api` forbids `cv2`/`anthropic` imports outside their packages.

## Alternatives considered
- *Framework-centric (FastAPI everywhere)* — domain logic ends up in route handlers; untestable without HTTP.
