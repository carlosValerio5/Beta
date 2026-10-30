"""Claude-backed adapters, exercised against scripted transports (no network)."""

from __future__ import annotations

import json

from beta_core.domain.beta import BetaDraft, Contacts, Limb, MoveDraft, Technique
from beta_core.domain.holds import HoldType
from beta_core.domain.motion import MotionDraft, MoveDirection
from beta_core.domain.violations import Violation, ViolationCode
from beta_core.ports import BetaRequest, MotionRequest
from beta_core.testing import FAKE_IMAGE as IMAGE
from beta_core.testing import FakeMarkRenderer, ladder_holds, ladder_plan
from beta_core.validation import BetaValidator, MotionSpecValidator
from beta_llm.classifier import ClaudeHoldClassifier, HoldTypeDraft, HoldTypeGuess
from beta_llm.director import ClaudeMotionDirector
from beta_llm.planner import ClaudeBetaPlanner
from beta_llm.prompts import PromptRegistry
from beta_llm.transport import ScriptedTransport


def ladder_draft() -> BetaDraft:
    plan = ladder_plan()
    return BetaDraft(
        start=plan.start,
        moves=[
            MoveDraft(limb=m.limb, hold_id=m.hold_id, technique=m.technique, cue=m.cue)
            for m in plan.moves
        ],
        crux_move_indices=list(plan.crux_move_indices),
        summary=plan.summary,
        grade_estimate="V3",
        confidence=0.7,
    )


def test_planner_returns_valid_plan_with_provenance(
    registry: PromptRegistry, beta_request: BetaRequest
) -> None:
    transport = ScriptedTransport(ladder_draft().model_dump_json())
    plan = ClaudeBetaPlanner(transport, registry).plan(beta_request)

    assert plan.id == "bet_1"
    assert plan.provenance.prompt == "beta_planner@v1"
    assert plan.provenance.model == "claude-opus-5-5"
    assert (
        BetaValidator().validate(
            plan, beta_request.problem, body=beta_request.body, px_per_cm=beta_request.px_per_cm
        )
        == []
    )

    params, _ = transport.calls[0]
    text = params["messages"][0]["content"][-1]["text"]
    assert '"id": 8' in text  # hold table is in the prompt
    assert "175" in text  # climber height


def test_planner_includes_repair_feedback(
    registry: PromptRegistry, beta_request: BetaRequest
) -> None:
    violation = Violation(code=ViolationCode.NOT_FINISHED, message="End matched on hold 8.")
    repair = beta_request.model_copy(
        update={"previous_attempt": ladder_plan(), "previous_violations": (violation,)}
    )
    transport = ScriptedTransport(ladder_draft().model_dump_json())
    ClaudeBetaPlanner(transport, registry).plan(repair)
    text = transport.calls[0][0]["messages"][0]["content"][-1]["text"]
    assert "End matched on hold 8." in text
    assert "not_finished" in text


def test_director_assembles_valid_spec(
    registry: PromptRegistry, motion_request: MotionRequest
) -> None:
    draft = MotionDraft(
        directions=[
            MoveDirection(move_index=-1, duration_s=2.0, caption="Hands on the starts"),
            MoveDirection(
                move_index=7, duration_s=1.5, slow_motion=True, show_trail=True, callout="Crux"
            ),
        ]
    )
    transport = ScriptedTransport(draft.model_dump_json())
    spec = ClaudeMotionDirector(transport, registry).direct(motion_request)

    assert spec.provenance.prompt == "motion_director@v1"
    assert spec.keyframes[8].slow_motion
    assert MotionSpecValidator().validate(spec, motion_request.beta) == []
    text = transport.calls[0][0]["messages"][0]["content"][-1]["text"]
    assert '"move_index": 7' in text


def test_classifier_merges_types(registry: PromptRegistry) -> None:
    holds = list(ladder_holds())
    guess = HoldTypeDraft(
        holds=[
            HoldTypeGuess(id=0, hold_type=HoldType.SLOPER),
            HoldTypeGuess(id=99, hold_type=HoldType.JUG),  # unknown id ignored
        ]
    )
    transport = ScriptedTransport(guess.model_dump_json())
    out = ClaudeHoldClassifier(transport, registry, FakeMarkRenderer()).classify(IMAGE, holds)
    assert out[0].hold_type is HoldType.SLOPER
    assert out[1:] == holds[1:]
    params, fallbacks = transport.calls[0]
    assert params["model"] == "claude-haiku-5-5"
    assert fallbacks is False


def test_draft_json_roundtrip() -> None:
    draft = BetaDraft(
        start=Contacts(lh=0, rh=1),
        moves=[MoveDraft(limb=Limb.LH, hold_id=4, technique=Technique.REACH)],
    )
    assert BetaDraft.model_validate(json.loads(draft.model_dump_json())) == draft
