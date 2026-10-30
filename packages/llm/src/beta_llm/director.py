"""``MotionDirector`` backed by Claude (prompt: ``prompts/motion_director``)."""

from __future__ import annotations

import json

from beta_core.choreography import assemble_motion_spec
from beta_core.domain.beta import BetaPlan, Provenance
from beta_core.domain.climber import BodyModel
from beta_core.domain.motion import MotionDraft, MotionSpec
from beta_core.ports import MotionRequest
from beta_llm.claude import StructuredCaller
from beta_llm.planner import holds_table, repair_section
from beta_llm.prompts import PromptRegistry
from beta_llm.transport import Transport

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30


def beta_json(plan: BetaPlan) -> str:
    return json.dumps(
        {
            "start": plan.start.model_dump(),
            "moves": [
                {
                    "move_index": m.index,
                    "limb": m.limb.value,
                    "hold_id": m.hold_id,
                    "technique": m.technique.value,
                    "cue": m.cue,
                }
                for m in plan.moves
            ],
            "crux_move_indices": list(plan.crux_move_indices),
            "summary": plan.summary,
        },
        indent=1,
    )


def describe_body(body_px: BodyModel) -> str:
    return (
        f"Torso {body_px.torso:.0f}, shoulder width {body_px.shoulder_width:.0f}, hip width "
        f"{body_px.hip_width:.0f}, upper arm {body_px.upper_arm:.0f} + forearm {body_px.forearm:.0f} "
        f"(reach {body_px.arm_length:.0f}), thigh {body_px.thigh:.0f} + shin {body_px.shin:.0f} "
        f"(reach {body_px.leg_length:.0f})."
    )


class ClaudeMotionDirector:
    name = "claude-motion-director@1"

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

    def direct(self, request: MotionRequest) -> MotionSpec:
        prompt = self._registry.get("motion_director", self._prompt_version)
        previous = (
            json.dumps(
                [
                    k.model_dump(
                        mode="json", include={"move_index", "hip", "camera", "duration_frames"}
                    )
                    for k in request.previous_spec.keyframes
                ]
            )
            if request.previous_spec
            else None
        )
        user = prompt.render_user(
            beta_json=beta_json(request.beta),
            holds_json=holds_table(request.problem, request.px_per_cm),
            body=describe_body(request.body.scaled(request.px_per_cm)),
            image_width=request.image_ref.width,
            image_height=request.image_ref.height,
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            fps=FPS,
            repair=repair_section(previous, request.previous_violations),
        )
        result = self._caller.call(
            prompt, user_text=user, images=[request.image], output=MotionDraft
        )
        return assemble_motion_spec(
            result.value,
            plan=request.beta,
            problem=request.problem,
            image=request.image_ref,
            body_cm=request.body,
            px_per_cm=request.px_per_cm,
            provenance=Provenance(planner=self.name, prompt=result.prompt_ref, model=result.model),
            fps=FPS,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
        )
