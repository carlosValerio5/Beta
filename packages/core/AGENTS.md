# beta_core — agent notes

The hexagon's inside. Everything else in the repo depends on this package; it depends only on
Pydantic.

| Module | Holds |
|---|---|
| `domain/geometry.py` | `Point`, `BBox` (pixel space of the normalised image) |
| `domain/holds.py` | `Hold`, `HoldType`, `Problem` |
| `domain/grades.py` | `Grade` (V-scale ⇄ Font) |
| `domain/climber.py` | `ClimberProfile`, `BodyModel` (anthropometrics) |
| `domain/beta.py` | `Limb`, `Technique`, `Move`, `BetaPlan`, `Provenance` |
| `domain/motion.py` | MotionSpec DSL (`MotionSpec`, `Keyframe`, annotations, `MotionDraft`) |
| `domain/records.py` | Aggregates with lifecycle: `Analysis`, `BetaRecord`, `VideoRecord` |
| `domain/events.py` | `DomainEvent` (what lands in bronze) |
| `kinematics.py` | Limb roots, reach checks, two-bone IK, `best_hip` search |
| `scale.py` | px/cm estimation |
| `validation.py` | `BetaValidator`, `MotionSpecValidator`, `Violation` |
| `choreography.py` | `assemble_motion_spec` (MotionDraft + BetaPlan → MotionSpec) |
| `ports.py` | Protocols every adapter implements |
| `services/` | Use cases: analyze, select problem, generate beta, generate video, feedback |
| `contracts.py` | Exports JSON Schema + fixtures into `/contracts` (`python -m beta_core.contracts`) |

Rules:
- No imports from `beta_vision`, `beta_llm`, `beta_data`, `beta_api`, or any I/O library.
- Domain models are frozen Pydantic models; mutate with `model_copy(update=...)`.
- Kinematics changes must keep `contracts/kinematics/fixtures.json` in sync (the renderer tests
  read it): run `make contracts`.
