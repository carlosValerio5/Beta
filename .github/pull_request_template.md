## What

<!-- One paragraph: what changes and why. Link the issue / ADR. -->

## How it was verified

- [ ] `make lint typecheck test`
- [ ] `make contracts-check` (if models, API or MotionSpec changed)
- [ ] `make eval` (if prompts, planner, director or validators changed)
- [ ] Screenshots / rendered video frames (if UI or renderer changed)

## Checklist

- [ ] Tests written first (RED → GREEN)
- [ ] Docs updated (`docs/`, package `AGENTS.md`, ADR if a decision changed)
- [ ] No released prompt version edited in place (add a new `vN.md` instead)
- [ ] No writes to `data/bronze` outside `beta_data.bronze`
- [ ] CHANGELOG entry under *Unreleased*
