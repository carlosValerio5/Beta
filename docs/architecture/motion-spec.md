# MotionSpec DSL (v1)

The route video is a pure function of a **MotionSpec** (ADR-0010). Schema:
`contracts/motion-spec/v1.schema.json`; examples: `contracts/motion-spec/examples/`.

## Two layers

| Layer | Written by | Contains |
|---|---|---|
| `MotionDraft` | motion director (Claude or `ChoreographyDirector`) | per-move `duration_s`, `easing`, optional `hip`, optional `camera`, `caption` (≤60), `callout` (≤40), `slow_motion`, `show_trail` |
| `MotionSpec` | `assemble_motion_spec` (code) | resolved frames, contacts copied from the beta, hips, cameras, annotations, chapters, body in px, holds |

The director decides *how* to show the beta; it cannot change *what* the beta is.

## MotionSpec fields

```
version: "1"            beta_id        provenance {planner, prompt, model}
meta {fps, width, height, duration_frames}       image {uri, width, height}
px_per_cm               body {unit: px, torso, upper_arm, forearm, thigh, shin, …}
holds[] {id, center, radius, color, role: start|top|route}
keyframes[] {
  move_index (-1 = start pose), start_frame, duration_frames,
  contacts {lh, rh, lf, rf}, hip, limb, technique, easing, camera {center, zoom},
  annotations[]: highlight | arrow | caption | callout | trail,  slow_motion
}
chapters[] {move_index, start_frame, title}
```

## Semantics

- A keyframe is the pose *reached at the end* of its segment; the renderer interpolates from the
  previous keyframe (hip eased, moving limb on an arc, other limbs fixed).
- `camera.zoom = 1` shows the whole photo inside the 9:16 frame; the renderer never pans past an
  edge.
- Defaults when the director omits something: start pose 1.6 s, moves 1.2 s, dynamic moves 0.8 s
  with `snap` easing, crux in slow motion (×1.75), hip from `natural_hip`, camera auto-framed.

## Changing the DSL

1. Change the Pydantic models in `beta_core/domain/motion.py` (bump `version` if not additive).
2. `make contracts`.
3. Mirror it in `apps/renderer/src/spec.ts`; renderer tests parse every example.
4. Update this page and `docs/agents/motion-director.md`.
