# 0009 — Route videos instead of coach chat

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The first plan had a "coach chat" for follow-up questions. The product owner rejected it: climbers
learn movement by watching, and a chat adds a conversational surface that is hard to evaluate.

## Decision
Every beta gets an explanatory **route video**. Claude acts as a *motion director*: given the beta,
the photo and the climber's body, it decides pacing, camera framing, emphasis and captions. Feedback
is attached to moves (chapters), not to conversation turns.

## Consequences
- New pipeline stage (direct → validate → render) and a renderer service.
- Per-move feedback ("looks wrong", rewatches) is a sharper signal than chat logs.
- Follow-up questions are answered by alternative betas (roadmap v0.2), not chat.

## Alternatives considered
- *Coach chat* — rejected by owner. *Static annotated image only* — kept as the poster/fallback.
