@AGENTS.md

## Claude Code specifics

- Prefer `make` targets over ad-hoc commands; they encode the right flags.
- Before touching Anthropic SDK code in `packages/llm`, re-read `docs/agents/` and the prompt you are
  changing; model IDs and defaults live in prompt front matter, not in code.
- For any change to `beta_core` models, finish with `make contracts` and run the renderer + BetaKit
  fixture tests — they are the cross-language contract.
- Never run `make eval-live` or anything marked `live` without the user asking: it spends API credit.
