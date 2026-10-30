# Runbook

## Run everything locally

```bash
make dev        # API :8000 + renderer :8787 (renderer downloads headless Chrome on first render)
make smoke      # photo → beta → MP4 over HTTP; results in var/e2e/smoke/
```

`GET /health` shows which planner/director are active and whether a renderer is attached.

## Symptoms

| Symptom | Likely cause | Fix |
|---|---|---|
| Betas `failed` with `upstream_error` | Anthropic API error or refusal | Check logs for the request id; retry; unset the key to fall back to heuristics |
| Videos stop at `directed` | No `BETA_RENDERER_URL` | Start `make renderer` and set the URL |
| Videos `failed: renderer unreachable` | Renderer down | `make renderer`; check port 8787 |
| Remotion warns about version mismatch | Package drift | Keep all `@remotion/*` at one version; `zod` exactly as Remotion requires |
| `make contracts-check` fails | Model/API changed without regenerating | `make contracts`, update BetaKit/renderer, commit |
| iOS can't reach the API on a device | Device can't see `localhost` | Profile → Server → your Mac's LAN IP |

## Data

```bash
make seed data          # synthetic walls → bronze → silver → gold
uv run beta-data status # row counts per table
```

**Deletion request** for a device: remove its rows from `var/beta.sqlite3`, then filter its events
and images out of a *new* bronze snapshot (`device_id` in `image.ingested`), rebuild silver/gold,
and `dvc push` the new version. Never edit bronze files in place.

## Evals

`make eval` must pass before merging prompt, planner, director or validator changes.
