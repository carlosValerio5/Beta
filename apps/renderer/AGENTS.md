# @beta/renderer — agent notes

Turns a MotionSpec (contracts/motion-spec/v1.schema.json) into a 9:16 MP4 with Remotion.
The renderer is a pure function of the spec: no network, no randomness, no clock.

| Path | Does |
|---|---|
| `src/spec.ts` | zod mirror of the Python `MotionSpec` (must parse every `contracts/motion-spec/examples/*.json`) |
| `src/kinematics.ts` | Port of `beta_core.kinematics` (must match `contracts/kinematics/fixtures.json` to 1e-6) |
| `src/timeline.ts` | Segment lookup, easing, camera interpolation and the camera→screen transform |
| `src/pose.ts` | Climber skeleton for any frame (hip + limb ends → two-bone IK) |
| `src/components/` | React/SVG scene: wall, holds, annotations, climber, HUD |
| `src/Root.tsx`, `src/index.ts` | Remotion composition `RouteVideo` (metadata from the spec) |
| `src/server/` | `POST /render` → `{video_base64, poster_base64, duration_s}`; `GET /health` |
| `scripts/render-fixture.ts` | Renders the directed ladder fixture to `var/renders/` |

Rules:
- Change the spec shape only in Python first (`make contracts`), then mirror it in `spec.ts`.
- Keep math in plain `.ts` modules with vitest tests; components only draw what those return.
- Colours come from `contracts/palette.json`, never hard-coded in components.
- Remotion licence: free for individuals/small teams — see ADR-0011 before commercial use.
