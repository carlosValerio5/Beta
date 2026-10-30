# beta_api — agent notes

The composition root. This is the only place that knows which adapter implements which port.

| Module | Does |
|---|---|
| `settings.py` | `Settings` (env prefix `BETA_`) |
| `container.py` | Builds adapters + use cases from settings (Claude vs heuristic, renderer vs none) |
| `repositories.py` | SQLite repositories (JSON payload per aggregate) |
| `media.py` | `LocalMediaStore`: normalised images, overlays, videos under `var/media` |
| `renderer.py` | `RemotionHttpRenderer` (`VideoRenderer` port) |
| `schemas.py` | HTTP request/response models (wire format; mirrors BetaKit) |
| `routes/` | `analyses`, `betas`, `videos`, `health` routers |
| `jobs.py` | Background job runners (beta + video) |
| `openapi.py` | `python -m beta_api.openapi <path>` exports the OpenAPI document |

Rules:
- Routes are thin: parse → call a use case → map to a schema. No domain logic here.
- Long work (beta, video) returns `202` + a resource with `status`; clients poll.
- Changing a response shape = `make contracts` + BetaKit model update + `contracts/api/examples`.
