import pytest

from beta_core.choreography import assemble_motion_spec
from beta_core.domain.beta import BetaPlan, Limb, Provenance, Technique
from beta_core.domain.climber import BodyModel
from beta_core.domain.geometry import Point
from beta_core.domain.holds import Problem
from beta_core.domain.motion import (
    Callout,
    Camera,
    Caption,
    HoldHighlight,
    ImageRef,
    MotionDraft,
    MotionSpec,
    MoveDirection,
    Trail,
)
from beta_core.testing import LADDER_IMAGE
from beta_core.validation import MotionSpecValidator, ViolationCode

PROV = Provenance(planner="test@1")


def assemble(
    plan: BetaPlan,
    problem: Problem,
    body_cm: BodyModel,
    px_per_cm: float,
    draft: MotionDraft | None = None,
) -> MotionSpec:
    return assemble_motion_spec(
        draft or MotionDraft(directions=[]),
        plan=plan,
        problem=problem,
        image=LADDER_IMAGE,
        body_cm=body_cm,
        px_per_cm=px_per_cm,
        provenance=PROV,
    )


def test_default_spec_structure(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    assert len(spec.keyframes) == len(plan.moves) + 1
    assert [k.move_index for k in spec.keyframes] == list(range(-1, len(plan.moves)))
    assert len(spec.chapters) == len(plan.moves)
    assert spec.body.unit == "px"
    for prev, nxt in zip(spec.keyframes, spec.keyframes[1:], strict=False):
        assert nxt.start_frame == prev.start_frame + prev.duration_frames
    assert (
        spec.meta.duration_frames
        >= spec.keyframes[-1].start_frame + spec.keyframes[-1].duration_frames
    )
    assert [k.contacts for k in spec.keyframes] == plan.states()


def test_default_spec_passes_validator(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    assert MotionSpecValidator().validate(spec, plan) == []


def test_move_annotations(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    first_move = spec.keyframes[1]
    highlights = [a for a in first_move.annotations if isinstance(a, HoldHighlight)]
    assert highlights[0].hold_id == plan.moves[0].hold_id


def test_slow_motion_and_caption(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    draft = MotionDraft(
        directions=[
            MoveDirection(move_index=0, duration_s=1.0, slow_motion=True, caption="Lock off low"),
        ]
    )
    plain = assemble(
        plan,
        problem,
        body_cm,
        px_per_cm,
        MotionDraft(directions=[MoveDirection(move_index=0, duration_s=1.0)]),
    )
    slow = assemble(plan, problem, body_cm, px_per_cm, draft)
    assert slow.keyframes[1].duration_frames > plain.keyframes[1].duration_frames
    assert slow.keyframes[1].slow_motion
    captions = [a for a in slow.keyframes[1].annotations if isinstance(a, Caption)]
    assert captions[0].text == "Lock off low"


def test_dynamic_moves_get_trails_and_callouts(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    moves = list(plan.moves)
    moves[0] = moves[0].model_copy(update={"technique": Technique.DEADPOINT})
    spec = assemble(plan.model_copy(update={"moves": tuple(moves)}), problem, body_cm, px_per_cm)
    kinds = {type(a) for a in spec.keyframes[1].annotations}
    assert Trail in kinds
    assert Callout in kinds


def test_crux_is_slowed_by_default(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    crux = plan.crux_move_indices[0]
    assert spec.keyframes[crux + 1].slow_motion


def test_auto_camera_inside_image(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    for k in spec.keyframes:
        assert 0 <= k.camera.center.x <= spec.image.width
        assert 0 <= k.camera.center.y <= spec.image.height


def test_validator_catches_contact_mismatch(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    frames = list(spec.keyframes)
    frames[2] = frames[2].model_copy(
        update={"contacts": frames[2].contacts.with_contact(Limb.LF, None)}
    )
    tampered = spec.model_copy(update={"keyframes": tuple(frames)})
    assert ViolationCode.CONTACTS_MISMATCH in {
        v.code for v in MotionSpecValidator().validate(tampered, plan)
    }


def test_validator_catches_unreachable_hip(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    frames = list(spec.keyframes)
    frames[1] = frames[1].model_copy(update={"hip": Point(x=50, y=50)})
    tampered = spec.model_copy(update={"keyframes": tuple(frames)})
    violations = MotionSpecValidator().validate(tampered, plan)
    assert any(v.code is ViolationCode.HIP_UNREACHABLE and v.move_index == 0 for v in violations)


def test_validator_catches_camera_out_of_frame(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    frames = list(spec.keyframes)
    frames[0] = frames[0].model_copy(
        update={"camera": Camera(center=Point(x=-500, y=10), zoom=1.0)}
    )
    tampered = spec.model_copy(update={"keyframes": tuple(frames)})
    assert ViolationCode.CAMERA_OUT_OF_FRAME in {
        v.code for v in MotionSpecValidator().validate(tampered, plan)
    }


def test_validator_catches_unknown_annotation_hold(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    frames = list(spec.keyframes)
    frames[1] = frames[1].model_copy(update={"annotations": (HoldHighlight(hold_id=999),)})
    tampered = spec.model_copy(update={"keyframes": tuple(frames)})
    assert ViolationCode.UNKNOWN_SPEC_HOLD in {
        v.code for v in MotionSpecValidator().validate(tampered, plan)
    }


def test_spec_json_roundtrip(
    plan: BetaPlan, problem: Problem, body_cm: BodyModel, px_per_cm: float
) -> None:
    spec = assemble(plan, problem, body_cm, px_per_cm)
    assert MotionSpec.model_validate_json(spec.model_dump_json()) == spec


def test_motion_draft_schema_is_tool_ready() -> None:
    schema = MotionDraft.model_json_schema()
    assert "directions" in schema["properties"]


@pytest.mark.parametrize("zoom", [0.5, 5.0])
def test_camera_zoom_bounds(zoom: float) -> None:
    with pytest.raises(ValueError, match="zoom"):
        Camera(center=Point(x=0, y=0), zoom=zoom)


def test_image_ref_is_plain() -> None:
    assert ImageRef(uri="x.jpg", width=10, height=20).height == 20
