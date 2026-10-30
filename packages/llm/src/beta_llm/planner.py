"""``BetaPlanner`` backed by Claude (prompt: ``prompts/beta_planner``)."""

from __future__ import annotations

import json
from collections.abc import Sequence

from beta_core.domain.beta import BetaDraft, BetaPlan, Provenance
from beta_core.domain.climber import BodyModel, ClimberProfile
from beta_core.domain.holds import Problem
from beta_core.domain.violations import Violation
from beta_core.ports import BetaRequest
from beta_llm.claude import StructuredCaller
from beta_llm.prompts import PromptRegistry
from beta_llm.transport import Transport


def holds_table(problem: Problem, px_per_cm: float) -> str:
    rows = [
        {
            "id": h.id,
            "x": round(h.center.x),
            "y": round(h.center.y),
            "size_cm": round(h.size / px_per_cm),
            "color": h.color,
            "type": h.hold_type.value,
            "role": problem.role_of(h.id),
        }
        for h in sorted(problem.holds, key=lambda h: h.id)
    ]
    return json.dumps(rows, indent=1)


def describe_climber(profile: ClimberProfile) -> str:
    return (
        f"Height {profile.height_cm:.0f} cm, ape index {profile.ape_index_cm:+.0f} cm "
        f"(wingspan {profile.wingspan_cm:.0f} cm). Max grade {profile.max_grade}. "
        f"Style: {profile.style.value}."
    )


def describe_reach(body_px: BodyModel) -> str:
    return (
        f"Arm (shoulder to fingertips) ≈ {body_px.arm_length:.0f} px, leg (hip to sole) ≈ "
        f"{body_px.leg_length:.0f} px, torso (hip to shoulders) ≈ {body_px.torso:.0f} px, "
        f"shoulder width ≈ {body_px.shoulder_width:.0f} px."
    )


def repair_section(previous: str | None, violations: Sequence[Violation]) -> str:
    if not violations:
        return ""
    lines = [
        "",
        "## Your previous answer was rejected",
        "Previous answer:",
        "```json",
        previous or "{}",
        "```",
        "The validator found:",
    ]
    for v in violations:
        where = f" (move {v.move_index})" if v.move_index is not None else ""
        lines.append(f"- [{v.code.value}] {v.message}{where}")
    lines.append("Fix every finding and keep what worked.")
    lines.append("")
    return "\n".join(lines)


def compact_plan(plan: BetaPlan) -> str:
    return json.dumps(
        {
            "start": plan.start.model_dump(),
            "moves": [
                {"limb": m.limb.value, "hold_id": m.hold_id, "technique": m.technique.value}
                for m in plan.moves
            ],
        }
    )


class ClaudeBetaPlanner:
    name = "claude-beta-planner@1"

    def __init__(
        self,
        transport: Transport,
        registry: PromptRegistry,
        *,
        prompt_version: int | None = None,
        model_override: str | None = None,
    ) -> None:
        self._caller = StructuredCaller(transport, model_override=model_override)
        self._registry = registry
        self._prompt_version = prompt_version

    def plan(self, request: BetaRequest) -> BetaPlan:
        prompt = self._registry.get("beta_planner", self._prompt_version)
        problem = request.problem
        user = prompt.render_user(
            climber=describe_climber(request.profile),
            start_ids=", ".join(str(i) for i in problem.start_hold_ids),
            top_id=problem.top_hold_id,
            color=problem.color or "mixed",
            image_width=request.image.width,
            image_height=request.image.height,
            px_per_cm=f"{request.px_per_cm:.2f}",
            holds_json=holds_table(problem, request.px_per_cm),
            reach=describe_reach(request.body.scaled(request.px_per_cm)),
            repair=repair_section(
                compact_plan(request.previous_attempt) if request.previous_attempt else None,
                request.previous_violations,
            ),
        )
        result = self._caller.call(prompt, user_text=user, images=[request.image], output=BetaDraft)
        return result.value.to_plan(
            plan_id=request.plan_id,
            analysis_id=request.analysis_id,
            provenance=Provenance(planner=self.name, prompt=result.prompt_ref, model=result.model),
        )
