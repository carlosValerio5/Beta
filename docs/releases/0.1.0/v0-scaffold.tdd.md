# TDD evidence — v0 scaffold (branch `feat/v0-scaffold`)

**Source plan:** the approved `/plan` in this session (revised: SwiftUI client, route videos via a
Claude-directed MotionSpec DSL instead of coach chat). No `*.plan.md` file; journeys come from
[PRD v0](../../product/prd.md).

## User journeys covered

1. Set up a profile → `ClimberProfile` (core), `ProfileView` + `ClimberProfile` RawRepresentable (iOS).
2. Capture a photo → `POST /v1/analyses`, GPS stripped, holds detected.
3. Select the problem → `PUT /v1/analyses/{id}/problem`, `HoldSelection` state machine.
4. Get a beta → planner + validator + repair loop; offline heuristic fallback.
5. Watch it climbed → MotionSpec → Remotion MP4 with chapters; `ChapterTimeline` in the app.
6. Give feedback → `POST /v1/betas/{id}/feedback`, playback signals into bronze → gold marts.
7. Logbook → SwiftData `ClimbLog`.

## RED → GREEN log

Every phase was a test commit (RED, run and failing for the intended reason) followed by an
implementation commit (GREEN).

| Phase | RED commit | RED evidence | GREEN commit | GREEN evidence |
|---|---|---|---|---|
| Core | `189d69c` | `ModuleNotFoundError: beta_core.domain` | `d77da34` | 119 passed, cov 96.6%, mypy strict clean |
| Vision | `85169d0` | `ModuleNotFoundError: beta_vision.preprocess` | `81920f6` | 22 passed; detector P/R/colour 1.00 on 8 seeds |
| LLM | `9b84fc5` | `ImportError: FAKE_IMAGE` (test support + modules missing) | `cdf1ffe` | 38 passed; SDK wire format checked via mock transport |
| Renderer | `ac0e01e` | vitest: 5 suites can't resolve `../src/*` | `78d7564` | 37 passed; Python↔TS kinematics parity to 1e-6; fixture MP4 rendered |
| Natural hips | `9f402c5` | 3 failing (`natural_hip` missing) | `78d7564` | core green; rendered frames reviewed |
| Data | (tests landed in `78d7564`)¹ | `ModuleNotFoundError: beta_data.layout` | `b99e2ed` | 22 passed |
| API | `8eb2e3a` | `ModuleNotFoundError: beta_api.app` | `c8e2f46` | 28 passed; total 232, cov 94.9% |
| iOS BetaKit | `5384a63` | 268 compile errors (`cannot find type 'Hold'`) | `d96e50e` | 28 Swift Testing tests passed |
| Evals | `d0cb680` | `ModuleNotFoundError: beta_evals.metrics` | `f0a2688` | 13 passed; offline eval PASSED |
| E2E fixes | `688c671`, `2466e4b` | knees-bend-outward, lowest-start-feet, feet-never-cross failing | `66e794d`, `72b7b09` | all suites green; eval back to 1.00 |

¹ The data-layer tests were written and run RED (output above) but went into the renderer GREEN
commit through `git add -A` before their own checkpoint commit. The RED run is recorded here.

## Test specification (highlights)

| # | Guaranteed | Where | Type |
|---|---|---|---|
| 1 | A beta referencing a hold outside the problem is rejected with the move index | `packages/core/tests/test_validation.py::test_unknown_hold_reports_move` | unit |
| 2 | Every pose of a valid beta is reachable for the climber's body | `test_validation.py::test_ladder_plan_is_valid_with_reach` | unit |
| 3 | Planner repairs use validator feedback; 3 bad attempts → failed, never half-valid | `test_services_beta.py` | unit |
| 4 | Video contacts can't diverge from the beta (contacts copied, validated) | `test_motion.py::test_validator_catches_contact_mismatch` | unit |
| 5 | GPS EXIF is removed before storage; other tags kept | `packages/vision/tests/test_preprocess.py` | unit |
| 6 | Claude calls use structured outputs, cached system, explicit effort, `fallbacks:"default"` on the wire | `packages/llm/tests/test_transport.py::test_real_sdk_serialises_fallbacks_and_structured_output` | integration |
| 7 | Bronze is content-addressed and never rewritten | `packages/data/tests/test_bronze.py` | unit |
| 8 | Silver rebuilds are idempotent; duplicate photos are flagged | `test_jobs.py` | integration |
| 9 | Full HTTP flow photo → beta → video, Range-served MP4 | `apps/api/tests/test_flow.py` | integration |
| 10 | Renderer kinematics equal Python's | `apps/renderer/tests/kinematics.test.ts` | contract |
| 11 | iOS decodes exactly what the API returns | `BetaKitTests/ContractDecodingTests` | contract |
| 12 | The pipeline meets thresholds on the golden set | `beta-eval run` (`evals/thresholds.json`) | eval |

## Final verification (2026-10-30)

| Command | Result |
|---|---|
| `uv run pytest` (per package) | core 122, vision 22, llm 40, data 22, api 28, evals 13 → **247 passed** |
| `uv run pytest --cov` | **94.88%** (gate 80%) |
| `npm test` | **38 passed** |
| `swift test --package-path apps/ios/Packages/BetaKit` | **28 passed** |
| `make typecheck` | mypy strict: no issues in 76 files; `tsc --noEmit` clean |
| `make lint` | ruff + biome clean (swiftlint not installed — skipped) |
| `make contracts-check` | no drift |
| `make seed data` + `make eval` (gold golden set, 12 cases) | beta success 1.00, spec valid 1.00, detection P/R 1.00 → PASSED |
| `dvc repro` / `dvc status` | pipeline reproduced; "Data and pipelines are up to date" |
| `scripts/e2e_smoke.py` against live API + renderer | 30 holds → 10-move V4 beta (1.1 s) → 10-chapter MP4 rendered, 10.1 s total |
| `mkdocs build --strict` | built |

## Known gaps

- **iOS app target not built** — Xcode isn't installed. Views typecheck against the macOS SDK
  (iOS-only views stubbed) except SwiftData `@Model`, whose macro plugin ships only with Xcode.
  `make ios` and the UI tests are unverified.
- **No live Claude run** — no `ANTHROPIC_API_KEY` in this session. Claude adapters are tested
  against scripted transports and a mock HTTP transport through the real SDK; prompt quality is
  unmeasured until `make eval-live`.
- **Synthetic data only** — detection metrics of 1.00 are on synthetic walls; real gym photos are
  the main open risk (roadmap v0.1).
- **SwiftLint** not installed locally; config is in place and CI installs it.
