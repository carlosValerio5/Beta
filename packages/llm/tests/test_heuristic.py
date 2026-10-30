from __future__ import annotations

from beta_core.domain.beta import Limb, Technique
from beta_core.ports import BetaRequest, MotionRequest
from beta_core.validation import BetaValidator, MotionSpecValidator
from beta_llm.heuristic import ChoreographyDirector, HeuristicBetaPlanner


def test_heuristic_plan_is_valid_and_reachable(beta_request: BetaRequest) -> None:
    plan = HeuristicBetaPlanner().plan(beta_request)
    violations = BetaValidator().validate(
        plan, beta_request.problem, body=beta_request.body, px_per_cm=beta_request.px_per_cm
    )
    assert violations == []
    assert plan.provenance.planner == HeuristicBetaPlanner.name


def test_heuristic_plan_starts_on_starts_and_matches_top(beta_request: BetaRequest) -> None:
    plan = HeuristicBetaPlanner().plan(beta_request)
    problem = beta_request.problem
    assert {plan.start.lh, plan.start.rh} <= set(problem.start_hold_ids)
    assert plan.moves[-1].technique is Technique.MATCH
    assert plan.final_contacts.lh == plan.final_contacts.rh == problem.top_hold_id


def test_heuristic_plan_is_deterministic(beta_request: BetaRequest) -> None:
    assert HeuristicBetaPlanner().plan(beta_request) == HeuristicBetaPlanner().plan(beta_request)


def test_heuristic_plan_moves_feet(beta_request: BetaRequest) -> None:
    plan = HeuristicBetaPlanner().plan(beta_request)
    assert any(not m.limb.is_hand for m in plan.moves)
    assert all(m.cue for m in plan.moves)
    assert len(plan.crux_move_indices) == 1


def test_short_climber_still_gets_a_plan(beta_request: BetaRequest) -> None:
    from beta_core.domain.climber import BodyModel, ClimberProfile

    short = ClimberProfile(height_cm=155, ape_index_cm=-2)
    request = beta_request.model_copy(
        update={"profile": short, "body": BodyModel.from_profile(short)}
    )
    plan = HeuristicBetaPlanner().plan(request)
    assert plan.moves
    assert {m.limb for m in plan.moves} >= {Limb.LH, Limb.RH}


def test_choreography_director_spec_is_valid(motion_request: MotionRequest) -> None:
    spec = ChoreographyDirector().direct(motion_request)
    assert MotionSpecValidator().validate(spec, motion_request.beta) == []
    crux = motion_request.beta.crux_move_indices[0]
    assert spec.keyframes[crux + 1].slow_motion
    assert spec.provenance.planner == ChoreographyDirector.name
    assert spec.keyframes[0].duration_frames > spec.keyframes[1].duration_frames
