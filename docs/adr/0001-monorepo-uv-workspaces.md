# 0001 — Monorepo with uv workspaces

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The product spans Python (CV, LLM, data, API), TypeScript (renderer) and Swift (iOS). Contracts
between them (MotionSpec, API shapes) change together, and a solo developer needs one place to run
everything.

## Decision
One repository. Python packages are members of a single **uv workspace** with one lockfile
(`uv.lock`); each package lives in `packages/<name>/src/beta_<name>` with its own `pyproject.toml`
and `tests/`. Apps live in `apps/`. A root `Makefile` is the single entrypoint.

## Consequences
- Cross-package refactors are one PR; `make contracts-check` catches cross-language drift.
- Each package declares its own dependencies, so layering is visible in `pyproject.toml`.
- CI runs all suites; we keep them fast to keep that tolerable.

## Alternatives considered
- *Polyrepo* — contract drift across repos, too much ceremony for one developer.
- *Single Python package* — hides layering; OpenCV/Anthropic would leak into the core.
