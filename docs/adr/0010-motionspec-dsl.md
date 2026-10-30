# 0010 — MotionSpec DSL instead of generated animation code

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Claude could write animation code (e.g. Remotion TSX) directly. That would be expressive, but means
running model-written code on our servers and makes outputs hard to validate, test and cache.

## Decision
Claude writes a **MotionDraft**: per-move duration, easing, hip position, camera framing and
annotations. Core code (`assemble_motion_spec`) merges it with the BetaPlan — limb contacts always
come from the beta, never from the director — into a **MotionSpec** (versioned JSON, schema in
`contracts/motion-spec/`). A validator checks reachability (2D IK), timing and framing. The renderer
is a pure function of the spec.

## Consequences
- Contacts in the video cannot disagree with the beta by construction.
- Unreachable poses feed back into beta repair — the video stage doubles as a kinematics check.
- Expressiveness is bounded by the DSL; new effects need a schema version bump.

## Alternatives considered
- *Generated Remotion code in a sandbox* — security + validation cost.
- *Hybrid vetted effect library* — a natural v0.2 extension of the DSL's annotation types.
