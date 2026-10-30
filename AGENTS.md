# AGENTS.md — working in the Beta Climbing repo

This file is for coding agents (Claude Code, Codex, Cursor, …) and humans who work like them.
Each package has its own `AGENTS.md` with local rules; read the one nearest the file you edit.
Docs about the AI agents *inside the product* (beta planner, motion director, hold classifier)
live in [`docs/agents/`](docs/agents/README.md).

## What this product does

A climber photographs a boulder problem. The app detects the holds, the climber confirms which ones
belong to the problem, and we produce:

1. a **BetaPlan**: ordered moves (limb → hold, technique, cue), crux, grade estimate;
2. a **route video**: a stylised climber figure performs the beta over the photo. Claude acts as a
   motion director and writes a declarative **MotionSpec** timeline; a deterministic Remotion
   renderer turns it into an MP4 with one chapter per move.

## Repo map

| Path | What | Language |
|---|---|---|
| `packages/core` (`beta_core`) | Domain model, ports (Protocols), use cases, validators, kinematics. **No I/O.** | Python |
| `packages/vision` (`beta_vision`) | Image preprocessing, hold detection, overlays, synthetic walls | Python |
| `packages/llm` (`beta_llm`) | Claude adapters, prompt registry, heuristic (offline) planner/director | Python |
| `packages/data` (`beta_data`) | Medallion lakehouse: bronze writers, silver/gold jobs, contracts, lineage | Python |
| `apps/api` (`beta_api`) | FastAPI composition root + HTTP adapters, SQLite repos, background jobs | Python |
| `apps/renderer` (`@beta/renderer`) | Remotion compositions + render service (MotionSpec → MP4) | TypeScript |
| `apps/ios` | SwiftUI app (`BetaApp`) + `BetaKit` Swift package (models, client, view models) | Swift |
| `evals` (`beta_evals`) | Golden-set eval harness, metrics, LLM cassettes | Python |
| `prompts/` | Versioned prompts (`<name>/vN.md`) | Markdown |
| `contracts/` | Generated cross-language contracts (JSON Schema, OpenAPI, fixtures) | JSON |
| `data/` | Medallion layers (bronze/silver/gold), versioned with DVC, contents gitignored | — |
| `docs/` | Product, architecture, ADRs, data, agent docs, guides (mkdocs) | Markdown |

## Commands

```bash
make bootstrap        # install everything
make test             # python + renderer + BetaKit tests
make lint typecheck   # ruff, mypy --strict, eslint/tsc
make contracts        # regenerate contracts/ after changing domain models or API
make seed data        # synthetic walls -> bronze -> silver -> gold
make eval             # offline eval gate
make dev              # API :8000 + renderer :8787
```

## Non-negotiable rules

1. **TDD.** Write the failing test first, run it, see RED for the right reason, then implement.
2. **Layering (ADR-0002).** `beta_core` imports nothing from other `beta_*` packages and nothing that
   does I/O (no OpenCV, Anthropic, sqlite, filesystem). Adapters depend on core, never the reverse.
   Ruff's banned-api rule enforces part of this.
3. **Contracts are generated.** Never hand-edit `contracts/`. Change the Pydantic model, run
   `make contracts`, update the TypeScript zod schema / Swift models, and keep the cross-language
   fixture tests green.
4. **Prompts are immutable once released.** To change behaviour, add `prompts/<name>/v(N+1).md`
   and bump the default in front matter. Every LLM call records `prompt_name@version` + model.
5. **Bronze is append-only.** Only `beta_data.bronze` writes to `data/bronze`. Never edit or delete
   bronze files; fix data downstream in silver.
6. **Privacy.** GPS EXIF is stripped before anything is written (ADR-0007). Never log image bytes,
   API keys, or device identifiers in plain text.
7. **The LLM never decides geometry alone.** Holds come from detection + user confirmation; moves
   reference hold IDs; every BetaPlan and MotionSpec passes the deterministic validators.
8. **Offline first.** Everything (tests, evals, the app) must work without `ANTHROPIC_API_KEY`
   by falling back to the heuristic planner/director. Live calls are marked `@pytest.mark.live`.

## Conventions

- Python 3.12+, Pydantic v2 frozen models for domain types, `Protocol` for ports, `typer` CLIs.
- Errors: domain errors subclass `beta_core.errors.BetaError`; adapters wrap third-party errors.
- Tests live in `<package>/tests/`, named `test_<unit>.py`, Arrange-Act-Assert, no network.
- Commits: Conventional Commits (`feat(core): …`, `test(vision): …`, `docs(adr): …`).
- When a decision changes, write an ADR (`docs/adr/NNNN-title.md`) instead of rewriting history.
