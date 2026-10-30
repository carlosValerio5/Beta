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


def test_start_uses_the_lowest_reachable_feet() -> None:
    from beta_core.domain.climber import BodyModel, ClimberProfile
    from beta_core.testing import FAKE_IMAGE
    from beta_vision.synthetic import SyntheticWallGenerator

    wall = SyntheticWallGenerator(42).generate()
    problem = wall.problem()
    profile = ClimberProfile(height_cm=172)
    request = BetaRequest(
        plan_id="b",
        analysis_id="a",
        problem=problem,
        image=FAKE_IMAGE,
        profile=profile,
        body=BodyModel.from_profile(profile),
        px_per_cm=wall.px_per_cm,
    )
    plan = HeuristicBetaPlanner().plan(request)
    feet = [problem.hold(h).center.y for h in (plan.start.lf, plan.start.rf) if h is not None]
    lowest = max(h.center.y for h in problem.holds)
    assert feet
    assert max(feet) == lowest


def test_feet_never_cross_on_synthetic_walls() -> None:
    from beta_core.domain.climber import BodyModel, ClimberProfile
    from beta_core.testing import FAKE_IMAGE
    from beta_vision.synthetic import SyntheticWallGenerator

    for seed in range(40, 48):
        wall = SyntheticWallGenerator(seed).generate()
        problem = wall.problem()
        profile = ClimberProfile(height_cm=172)
        plan = HeuristicBetaPlanner().plan(
            BetaRequest(
                plan_id="b",
                analysis_id="a",
                problem=problem,
                image=FAKE_IMAGE,
                profile=profile,
                body=BodyModel.from_profile(profile),
                px_per_cm=wall.px_per_cm,
            )
        )
        for state in plan.states():
            if state.lf is not None and state.rf is not None and state.lf != state.rf:
                left, right = problem.hold(state.lf).center.x, problem.hold(state.rf).center.x
                assert left <= right + 10, f"seed {seed}: feet crossed"
