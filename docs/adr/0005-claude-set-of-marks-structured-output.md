# 0005 — Claude with set-of-marks grounding and forced tool output

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Vision-language models are good at reading climbing intent from a photo but unreliable at precise
geometry and prone to inventing holds.

## Decision
- We draw **numbered markers** on the problem's holds (set-of-marks) and send that image plus a JSON
  table of holds (id, centre, size, colour, type, role) and the climber's body model.
- Claude must answer by calling a single **forced tool** whose `input_schema` is generated from a
  Pydantic model (`BetaDraft`, `MotionDraft`). Moves reference hold IDs only.
- Deterministic validators check the result; violations are sent back for up to 2 repair rounds.
- Model IDs and prompts are versioned files in `prompts/`; every call records provenance.
- Defaults: `claude-opus-5-5` for planning and directing, `claude-haiku-5-5` for hold classification.

## Consequences
- Hallucinated holds become validation errors, not user-facing nonsense.
- We depend on detection + user selection for the hold set.

## Alternatives considered
- *Free-text answers parsed with regex* — brittle. *Coordinates instead of IDs* — unverifiable.
