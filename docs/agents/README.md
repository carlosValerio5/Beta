# AI agents in the product

Docs for the model-driven components *inside* Beta. (For coding agents working on this repo, see
[`AGENTS.md`](https://github.com/carlosValerio5/beta/blob/main/AGENTS.md).)

| Agent | Model | Prompt | Output | Offline fallback |
|---|---|---|---|---|
| [Beta planner](beta-planner.md) | `claude-opus-5-5`, effort high | `prompts/beta_planner/` | `BetaDraft` → `BetaPlan` | `HeuristicBetaPlanner` |
| [Motion director](motion-director.md) | `claude-opus-5-5`, effort high | `prompts/motion_director/` | `MotionDraft` → `MotionSpec` | `ChoreographyDirector` |
| [Hold classifier](hold-classifier.md) | `claude-haiku-5-5`, effort low | `prompts/hold_classifier/` | `HoldTypeDraft` | colour detector's shape guess |

## How every call is made (`beta_llm/claude.py`)

- **Structured outputs** — `output_config.format` with a JSON schema generated from the draft
  model (`beta_llm/schema.py` closes objects and drops unsupported keywords). Claude Opus 5.5
  rejects forced `tool_choice`, so no tool is forced.
- **Prompt caching** — the system prompt is a stable cached block; per-request data goes in the user
  turn.
- **Effort** — set explicitly from the prompt's front matter (Opus 5.5 defaults to `medium`).
  Thinking is adaptive and always on for Opus 5.5; we never send `thinking`.
- **Refusal fallback** — for Opus/Sonnet/Fable models, requests go through the beta endpoint with
  `fallbacks: "default"` (header `server-side-fallback-2026-07-01`), so a safety decline is retried
  on Anthropic's recommended model. Sent via `extra_body` because the installed SDK only types the
  list form; `tests/test_transport.py` checks the bytes on the wire.
- **Failure modes** — `refusal`/`max_tokens` stop reasons, missing text and schema mismatches
  raise `AdapterError`; the use case marks the job failed with the reason.
- **Provenance** — every plan/spec records `name@version`, prompt `name@vN` and the model that
  actually answered.

## Evaluating changes

```bash
make eval                                                # offline baseline
BETA_LIVE=1 uv run beta-eval run --cassettes evals/cassettes   # live, records responses
uv run beta-eval run --cassettes evals/cassettes         # replay those responses, no network
```

Never edit a released prompt; add `vN+1.md` and compare reports.
