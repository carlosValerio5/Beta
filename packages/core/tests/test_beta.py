from beta_core.domain.beta import (
    BetaDraft,
    BetaPlan,
    Contacts,
    Limb,
    MoveDraft,
    Provenance,
    Technique,
)
from beta_core.domain.climber import ClimbingStyle
from beta_core.domain.grades import Grade


def test_contacts_with_contact_is_immutable() -> None:
    c = Contacts(lh=0, rh=1)
    moved = c.with_contact(Limb.LH, 4)
    assert c.lh == 0
    assert moved.lh == 4
    assert moved.rh == 1


def test_contacts_get() -> None:
    c = Contacts(lh=0, rh=1, lf=2, rf=None)
    assert c.get(Limb.LF) == 2
    assert c.get(Limb.RF) is None


def test_limb_kinds() -> None:
    assert Limb.LH.is_hand
    assert not Limb.RF.is_hand
    assert set(Limb.hands()) == {Limb.LH, Limb.RH}
    assert set(Limb.feet()) == {Limb.LF, Limb.RF}


def test_technique_is_dynamic() -> None:
    assert Technique.DYNO.is_dynamic
    assert Technique.DEADPOINT.is_dynamic
    assert not Technique.REACH.is_dynamic


def test_plan_states(plan: BetaPlan) -> None:
    states = plan.states()
    assert len(states) == len(plan.moves) + 1
    assert states[0] == plan.start
    assert states[-1] == plan.final_contacts
    assert plan.final_contacts.lh == plan.final_contacts.rh


def test_draft_to_plan_assigns_indices_and_parses_grade() -> None:
    draft = BetaDraft(
        start=Contacts(lh=0, rh=1),
        moves=[
            MoveDraft(limb=Limb.LH, hold_id=4, technique=Technique.REACH, cue="Reach left"),
            MoveDraft(limb=Limb.RH, hold_id=4, technique=Technique.MATCH, cue="Match"),
        ],
        crux_move_indices=[0],
        summary="Short",
        grade_estimate="6C",
        confidence=0.7,
        style=ClimbingStyle.STATIC,
    )
    plan = draft.to_plan(
        plan_id="bet_1", analysis_id="ana_1", provenance=Provenance(planner="test@1")
    )
    assert [m.index for m in plan.moves] == [0, 1]
    assert plan.grade_estimate == Grade(v=5)
    assert plan.crux_move_indices == (0,)


def test_draft_tolerates_unparseable_grade() -> None:
    draft = BetaDraft(start=Contacts(lh=0, rh=0), moves=[], grade_estimate="???")
    plan = draft.to_plan(plan_id="b", analysis_id="a", provenance=Provenance(planner="t@1"))
    assert plan.grade_estimate is None


def test_draft_json_schema_is_tool_ready() -> None:
    schema = BetaDraft.model_json_schema()
    assert schema["type"] == "object"
    assert "moves" in schema["properties"]
