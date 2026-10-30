import pytest

from beta_core.domain.beta import BetaPlan, Contacts, Limb, Move
from beta_core.domain.climber import BodyModel
from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold, Problem
from beta_core.validation import BetaValidator, Severity, ViolationCode, is_valid


def codes(violations: list) -> set[ViolationCode]:  # type: ignore[type-arg]
    return {v.code for v in violations}


def with_moves(plan: BetaPlan, moves: list[Move]) -> BetaPlan:
    return plan.model_copy(update={"moves": tuple(moves)})


def test_ladder_plan_is_valid_with_reach(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    violations = BetaValidator().validate(plan, problem, body=body_cm, px_per_cm=px_per_cm)
    assert violations == []


def test_empty_beta(plan: BetaPlan, problem: Problem) -> None:
    assert ViolationCode.EMPTY_BETA in codes(BetaValidator().validate(with_moves(plan, []), problem))


def test_move_index_sequence(plan: BetaPlan, problem: Problem) -> None:
    moves = list(plan.moves)
    moves[1] = moves[1].model_copy(update={"index": 7})
    assert ViolationCode.MOVE_INDEX_SEQUENCE in codes(
        BetaValidator().validate(with_moves(plan, moves), problem)
    )


def test_unknown_hold_reports_move(plan: BetaPlan, problem: Problem) -> None:
    moves = list(plan.moves)
    moves[2] = moves[2].model_copy(update={"hold_id": 99})
    violations = BetaValidator().validate(with_moves(plan, moves), problem)
    unknown = [v for v in violations if v.code is ViolationCode.UNKNOWN_HOLD]
    assert unknown
    assert unknown[0].move_index == 2


def test_start_hand_not_on_start_hold(plan: BetaPlan, problem: Problem) -> None:
    bad = plan.model_copy(update={"start": plan.start.with_contact(Limb.LH, 4)})
    assert ViolationCode.START_NOT_ON_START_HOLDS in codes(BetaValidator().validate(bad, problem))


def test_start_hand_missing(plan: BetaPlan, problem: Problem) -> None:
    bad = plan.model_copy(update={"start": plan.start.with_contact(Limb.RH, None)})
    assert ViolationCode.START_HANDS_MISSING in codes(BetaValidator().validate(bad, problem))


def test_not_finished_without_match(plan: BetaPlan, problem: Problem) -> None:
    assert ViolationCode.NOT_FINISHED in codes(
        BetaValidator().validate(with_moves(plan, list(plan.moves[:-1])), problem)
    )


def test_no_op_move(plan: BetaPlan, problem: Problem) -> None:
    moves = list(plan.moves)
    first = moves[0]
    noop = Move(index=0, limb=Limb.LH, hold_id=plan.start.lh or 0)
    shifted = [m.model_copy(update={"index": m.index + 1}) for m in moves]
    del first
    assert ViolationCode.NO_OP_MOVE in codes(
        BetaValidator().validate(with_moves(plan, [noop, *shifted]), problem)
    )


def test_unreachable_move(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    far = Hold(id=50, bbox=BBox(x=480, y=-400, w=40, h=40), color="red")
    wider = problem.model_copy(update={"holds": (*problem.holds, far)})
    moves = list(plan.moves)
    moves[0] = moves[0].model_copy(update={"hold_id": 50})
    violations = BetaValidator().validate(
        with_moves(plan, moves), wider, body=body_cm, px_per_cm=px_per_cm
    )
    unreachable = [v for v in violations if v.code is ViolationCode.UNREACHABLE]
    assert unreachable
    assert unreachable[0].move_index == 0


def test_reach_skipped_without_body(plan: BetaPlan, problem: Problem) -> None:
    assert BetaValidator().validate(plan, problem) == []


def test_crux_index_out_of_range(plan: BetaPlan, problem: Problem) -> None:
    bad = plan.model_copy(update={"crux_move_indices": (len(plan.moves) + 3,)})
    assert ViolationCode.CRUX_INDEX_OUT_OF_RANGE in codes(BetaValidator().validate(bad, problem))


def test_is_valid_ignores_warnings(plan: BetaPlan, problem: Problem) -> None:
    from beta_core.validation import Violation

    warning = Violation(code=ViolationCode.NO_OP_MOVE, message="w", severity=Severity.WARNING)
    assert is_valid([warning])
    assert not is_valid([warning.model_copy(update={"severity": Severity.ERROR})])


@pytest.mark.parametrize("hand", [Limb.LH, Limb.RH])
def test_start_contacts_accept_single_start_hold_for_both_hands(
    plan: BetaPlan, problem: Problem, hand: Limb
) -> None:
    start_hold = problem.start_hold_ids[0]
    both_on_one = plan.start.with_contact(Limb.LH, start_hold).with_contact(Limb.RH, start_hold)
    del hand
    bad = plan.model_copy(update={"start": both_on_one})
    assert ViolationCode.START_NOT_ON_START_HOLDS not in codes(BetaValidator().validate(bad, problem))


def test_contacts_type_alias() -> None:
    assert Contacts().lh is None
