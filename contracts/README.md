# contracts/

**Generated — do not edit by hand.** `make contracts` regenerates everything here; CI fails if the
committed files differ (`make contracts-check`).

| File | Source | Consumed by |
|---|---|---|
| `motion-spec/v1.schema.json`, `draft.v1.schema.json` | `beta_core.domain.motion` | docs, renderer zod mirror |
| `motion-spec/examples/*.json` | `beta_core.contracts` (ladder fixture) | renderer tests, Remotion Studio |
| `beta-plan/v1.schema.json`, `examples/ladder.json` | `beta_core.domain.beta` | docs |
| `kinematics/fixtures.json` | `beta_core.kinematics` | renderer kinematics parity tests |
| `palette.json` | `beta_core.palette` | renderer, BetaKit `Palette` test |
| `openapi.json` | FastAPI app | API reference |
| `api/examples/*.json` | in-process API run (`beta_api.openapi`) | BetaKit contract decoding tests |
