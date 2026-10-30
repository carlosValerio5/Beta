# Contributing

## Setup

```bash
make bootstrap
cp .env.example .env   # optional: add ANTHROPIC_API_KEY for live betas
make test
```

iOS work additionally needs Xcode and `brew install xcodegen swiftlint swiftformat`.
See [docs/guides/dev-setup.md](docs/guides/dev-setup.md).

## Workflow

1. Branch from `main`: `feat/<area>-<topic>`, `fix/<area>-<topic>`, `docs/<topic>`.
2. Write the failing test, watch it fail, implement, refactor (see `AGENTS.md`).
3. Keep docs in the same PR as the code: package `AGENTS.md`, `docs/`, ADRs, CHANGELOG.
4. `make check` must pass locally before you open a PR.

## Where things go

| Change | Also update |
|---|---|
| Domain model / API shape | `make contracts`, renderer zod schema, BetaKit models |
| Prompt behaviour | new `prompts/<name>/vN.md`, `docs/agents/<agent>.md`, run `make eval` |
| New silver/gold table | `beta_data.contracts`, `docs/data/`, `dvc.yaml` |
| Architectural decision | `docs/adr/NNNN-*.md` |

## Commit messages

Conventional Commits: `type(scope): summary`. Types: `feat`, `fix`, `test`, `refactor`, `docs`,
`chore`, `ci`, `perf`, `data`. Scopes: `core`, `vision`, `llm`, `data`, `api`, `renderer`, `ios`,
`evals`, `docs`, `repo`.
