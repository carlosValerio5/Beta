# Motion director

**Job:** decide how a beta is *shown* — pacing, easing, hip placement, camera, words — so the route
video teaches the movement. Contacts are fixed by the beta.

## Inputs (`prompts/motion_director/v1.md`)

- Set-of-marks photo, hold table, body segment lengths in px.
- The beta as JSON (move index, limb, hold, technique, cue, crux, summary).
- Frame facts: photo size, output 1080×1920 at 30 fps.
- On repair: previous keyframes (hip, camera, timing) and validator findings.

## Output (`MotionDraft`)

`directions[]`, each optional per segment: `move_index` (-1 = opening pose), `duration_s`
(clamped 0.3–6 s), `easing` (linear, ease_in_out, ease_out, snap), `hip`, `camera {center, zoom}`
(zoom clamped 1–4), `caption` (≤60), `callout` (≤40), `slow_motion`, `show_trail`.
`assemble_motion_spec` turns it into a MotionSpec; omitted fields get defaults.

## Design brief given to the model

Clarity over spectacle; pace by difficulty; ~2 s opening; 15–30 s total; frame active limbs with
headroom, pull wide for the top-out; realistic hips or omit them; caption about half the moves.

## Guardrails

`MotionSpecValidator` (contacts, timing, camera inside the photo, reachable hips, chapters).
One repair round. A failed spec never reaches the renderer.
