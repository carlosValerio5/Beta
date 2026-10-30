# Kinematics

A deliberately simple 2D climber, shared by the validators (Python) and the renderer (TypeScript).

## Body

`BodyModel.from_profile` uses Drillis & Contini segment ratios (fractions of height): shoulder width
0.259, hip width 0.191, torso 0.288, thigh 0.245, shin+foot 0.285. Arm length is rescaled so
`2·arm + shoulder width = wingspan`, which is how the ape index enters. `scaled(px_per_cm)` converts
to image pixels.

## Skeleton

- **Torso** — fixed length from the hip, leaning halfway between vertical and the hands' centroid
  (`TORSO_BLEND = 0.5`).
- **Roots** — shoulders and hips spread perpendicular to the torso; the climber faces the wall, so
  their left is image-left.
- **Limbs** — analytic two-bone IK (`solve_two_bone`). The renderer picks the bend that puts knees
  and elbows on the outside of the body.

## Two hip searches

| Function | Question | Used by |
|---|---|---|
| `best_hip` | Is there *any* hip that reaches every contact? (minimax reach ratio) | validators, heuristic planner |
| `natural_hip` | Where would a climber hold their hips? (arms ~85% extended, legs ~75%, centred, hands above shoulders, feet below hips, no fully folded limbs) | default hips in MotionSpecs |

Both are grid searches with local refinement — fast enough (≈10 ms) and deterministic.

## Tolerances

Real climbers twist, flag and rock their hips toward the wall — things a 2D model can't see — so
reach is checked with slack: 108% of limb length for betas, 112% for MotionSpecs. The renderer
stretches limbs up to 15% (and folds fully when a hold is next to the shoulder) so contacts always
land on their holds.

## Parity

`python -m beta_core.contracts` writes `contracts/kinematics/fixtures.json`; the renderer's
`tests/kinematics.test.ts` must reproduce every case to 1e-6.
