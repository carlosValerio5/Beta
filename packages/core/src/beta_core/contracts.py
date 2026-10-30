"""Export cross-language contracts into ``contracts/`` (run via ``make contracts``).

Outputs are byte-stable (sorted keys, fixed fixtures) so ``make contracts-check`` can diff them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from beta_core.choreography import assemble_motion_spec
from beta_core.domain.beta import BetaPlan, Provenance
from beta_core.domain.climber import BodyModel
from beta_core.domain.motion import MotionDraft, MotionSpec, MoveDirection
from beta_core.kinematics import kinematics_fixtures
from beta_core.testing import (
    LADDER_IMAGE,
    LADDER_PX_PER_CM,
    ladder_plan,
    ladder_problem,
    profile_175,
)


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def ladder_motion_spec(directed: bool = False) -> MotionSpec:
    plan = ladder_plan()
    draft = MotionDraft(directions=[])
    if directed:
        crux = plan.crux_move_indices[0]
        draft = MotionDraft(
            directions=[
                MoveDirection(
                    move_index=-1, duration_s=2.0, caption="Sit tight, hands on the yellow starts"
                ),
                MoveDirection(move_index=0, duration_s=1.0, caption="Reach left to the jug"),
                MoveDirection(
                    move_index=crux,
                    duration_s=1.4,
                    slow_motion=True,
                    show_trail=True,
                    caption="Drive from the feet, snap the hold",
                    callout="Crux",
                ),
            ]
        )
    return assemble_motion_spec(
        draft,
        plan=plan,
        problem=ladder_problem(),
        image=LADDER_IMAGE,
        body_cm=BodyModel.from_profile(profile_175()),
        px_per_cm=LADDER_PX_PER_CM,
        provenance=Provenance(planner="fixture@1"),
    )


def export_contracts(root: Path) -> list[Path]:
    files: dict[str, str] = {
        "motion-spec/v1.schema.json": _dump(MotionSpec.model_json_schema()),
        "motion-spec/draft.v1.schema.json": _dump(MotionDraft.model_json_schema()),
        "motion-spec/examples/ladder.json": _dump(ladder_motion_spec().model_dump(mode="json")),
        "motion-spec/examples/ladder-directed.json": _dump(
            ladder_motion_spec(directed=True).model_dump(mode="json")
        ),
        "beta-plan/v1.schema.json": _dump(BetaPlan.model_json_schema()),
        "beta-plan/examples/ladder.json": _dump(ladder_plan().model_dump(mode="json")),
        "kinematics/fixtures.json": _dump(kinematics_fixtures()),
    }
    written: list[Path] = []
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str]) -> None:
    root = Path(argv[1]) if len(argv) > 1 else Path("contracts")
    for path in export_contracts(root):
        print(path)


if __name__ == "__main__":
    main(sys.argv)
