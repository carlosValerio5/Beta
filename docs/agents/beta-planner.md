# Beta planner

**Job:** given a marked photo, the problem's holds and one climber's body, return the move
sequence that climbs it.

## Inputs (user turn of `prompts/beta_planner/v1.md`)

- Set-of-marks photo (numbered rings on problem holds).
- Hold table: `id, x, y` (image px), `size_cm`, `color`, detector `type`, `role` (start/top/route).
- Climber: height, ape index, wingspan, max grade, style.
- Reach in pixels: arm, leg, torso, shoulder width.
- On repair: the previous answer and every validator finding (`[code] message (move n)`).

## Output (`BetaDraft`)

`start` contacts, `moves[]` (limb, hold_id, technique, cue ≤12 words), `crux_move_indices`,
`summary`, `grade_estimate`, `confidence`, `style`. Code assigns IDs and indices and parses the grade.

## Guardrails

- Only marked hold IDs; validator rejects anything else.
- Must start on start holds and finish matched on the top.
- Every pose must be reachable for *this* body (`best_hip` ≤ 108%).
- Up to 2 repair rounds; then the beta is `failed` with the findings, never shown half-valid.

## Known limitations (v0)

- No wall angle (slab vs overhang) yet — the planner infers it from the photo.
- Feet-only holds are not marked separately from hand holds.
- The heuristic fallback produces plain ladder-style beta; it is a floor, not a coach.
