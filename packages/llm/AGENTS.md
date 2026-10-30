# beta_llm — agent notes

Only this package imports the Anthropic SDK. Product-agent behaviour is documented in
[`docs/agents/`](../../docs/agents/README.md); keep those docs in step with code and prompts.

| Module | Implements |
|---|---|
| `prompts.py` | `PromptRegistry`: loads `prompts/<name>/vN.md` (front matter + `$var` template) |
| `claude.py` | Shared tool-use call helper: forced tool, prompt caching, retries, provenance |
| `planner.py` | `ClaudeBetaPlanner` (`BetaPlanner` port) |
| `director.py` | `ClaudeMotionDirector` (`MotionDirector` port) |
| `classifier.py` | `ClaudeHoldClassifier` (`HoldClassifier` port) |
| `heuristic.py` | `HeuristicBetaPlanner`, `ChoreographyDirector`: deterministic offline fallbacks |
| `cassette.py` | Record/replay wrapper around the Messages API for deterministic tests and evals |

Rules:
- Claude's output always goes through a forced tool call whose `input_schema` comes from a Pydantic
  model (`BetaDraft`, `MotionDraft`, …). Never parse free text.
- Model IDs come from prompt front matter (overridable via settings), never hard-coded in adapters.
- Tests use fakes or cassettes. Anything that hits the network is `@pytest.mark.live`.
