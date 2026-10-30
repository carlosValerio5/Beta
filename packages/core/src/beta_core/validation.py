"""Deterministic validators for BetaPlans and MotionSpecs (ADR-0005, ADR-0010).

Violations are returned, never raised: the generation use cases feed them back to the planner or
director as repair instructions.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from beta_core.domain.beta import BetaPlan, Contacts, Limb
from beta_core.domain.climber import BodyModel
from beta_core.domain.geometry import Point
from beta_core.domain.holds import Problem
from beta_core.domain.motion import Callout, HoldHighlight, MotionSpec, MoveArrow
from beta_core.domain.violations import Severity, Violation, ViolationCode
from beta_core.kinematics import best_hip, contact_points, max_reach_ratio

__all__ = [
    "BetaValidator",
    "MotionSpecValidator",
    "Severity",
    "Violation",
    "ViolationCode",
    "is_valid",
]

BETA_REACH_TOLERANCE = 1.08
SPEC_REACH_TOLERANCE = 1.12


def is_valid(violations: Iterable[Violation]) -> bool:
    return not any(v.severity is Severity.ERROR for v in violations)


def _err(code: ViolationCode, message: str, move_index: int | None = None) -> Violation:
    return Violation(code=code, message=message, move_index=move_index)


def _state_move_index(state_index: int) -> int | None:
    """State 0 is the start position; state i>0 is the result of move i-1."""
    return state_index - 1 if state_index > 0 else None


class BetaValidator:
    def __init__(self, reach_tolerance: float = BETA_REACH_TOLERANCE) -> None:
        self.reach_tolerance = reach_tolerance

    def validate(
        self,
        plan: BetaPlan,
        problem: Problem,
        body: BodyModel | None = None,
        px_per_cm: float | None = None,
    ) -> list[Violation]:
        out: list[Violation] = []
        ids = problem.hold_ids
        moves = plan.moves

        if not moves:
            out.append(_err(ViolationCode.EMPTY_BETA, "The beta has no moves."))
        if [m.index for m in moves] != list(range(len(moves))):
            out.append(
                _err(ViolationCode.MOVE_INDEX_SEQUENCE, "Move indices must be 0, 1, 2, … in order.")
            )

        out.extend(self._check_start(plan.start, problem))

        states = plan.states()
        for move, before in zip(moves, states, strict=False):
            if move.hold_id not in ids:
                out.append(
                    _err(
                        ViolationCode.UNKNOWN_HOLD,
                        f"Move {move.index} uses hold {move.hold_id}, which is not part of the problem.",
                        move.index,
                    )
                )
            elif before.get(move.limb) == move.hold_id:
                out.append(
                    _err(
                        ViolationCode.NO_OP_MOVE,
                        f"Move {move.index}: {move.limb.label} is already on hold {move.hold_id}.",
                        move.index,
                    )
                )

        final = states[-1]
        if moves and not (final.lh == final.rh == problem.top_hold_id):
            out.append(
                _err(
                    ViolationCode.NOT_FINISHED,
                    f"The beta must end with both hands matched on the top hold {problem.top_hold_id}.",
                )
            )

        for crux in plan.crux_move_indices:
            if not 0 <= crux < len(moves):
                out.append(
                    _err(ViolationCode.CRUX_INDEX_OUT_OF_RANGE, f"Crux index {crux} is not a move.")
                )

        has_unknown = any(v.code is ViolationCode.UNKNOWN_HOLD for v in out)
        if body is not None and px_per_cm is not None and not has_unknown:
            out.extend(self._check_reach(states, problem, body, px_per_cm))
        return out

    @staticmethod
    def _check_start(start: Contacts, problem: Problem) -> list[Violation]:
        out: list[Violation] = []
        for limb, hold_id in start.items():
            if hold_id is not None and hold_id not in problem.hold_ids:
                out.append(
                    _err(
                        ViolationCode.UNKNOWN_HOLD,
                        f"Start {limb.label} is on unknown hold {hold_id}.",
                    )
                )
        if start.lh is None or start.rh is None:
            out.append(
                _err(ViolationCode.START_HANDS_MISSING, "Both hands must start on a start hold.")
            )
        for hand in Limb.hands():
            hold_id = start.get(hand)
            if (
                hold_id is not None
                and hold_id in problem.hold_ids
                and hold_id not in problem.start_hold_ids
            ):
                out.append(
                    _err(
                        ViolationCode.START_NOT_ON_START_HOLDS,
                        f"{hand.label} starts on hold {hold_id}; start holds are {list(problem.start_hold_ids)}.",
                    )
                )
        return out

    def _check_reach(
        self, states: Sequence[Contacts], problem: Problem, body: BodyModel, px_per_cm: float
    ) -> list[Violation]:
        body_px = body.scaled(px_per_cm) if body.unit == "cm" else body
        out: list[Violation] = []
        for i, state in enumerate(states):
            points = contact_points(problem, state)
            if all(p is None for p in points.values()):
                continue
            _, ratio = best_hip(points, body_px)
            if ratio > self.reach_tolerance:
                where = "the start position" if i == 0 else f"move {i - 1}"
                out.append(
                    _err(
                        ViolationCode.UNREACHABLE,
                        f"After {where} no body position reaches every hold "
                        f"(needs {ratio:.0%} of limb length). Choose closer holds or move feet first.",
                        _state_move_index(i),
                    )
                )
        return out


class MotionSpecValidator:
    def __init__(self, reach_tolerance: float = SPEC_REACH_TOLERANCE) -> None:
        self.reach_tolerance = reach_tolerance

    def validate(self, spec: MotionSpec, plan: BetaPlan) -> list[Violation]:
        expected = list(range(-1, len(plan.moves)))
        if [k.move_index for k in spec.keyframes] != expected:
            return [
                _err(
                    ViolationCode.KEYFRAME_SEQUENCE,
                    f"Keyframes must cover move indices {expected[0]}..{expected[-1]} in order.",
                )
            ]

        out: list[Violation] = []
        holds = {h.id: h.center for h in spec.holds}
        frame = 0
        for keyframe, state in zip(spec.keyframes, plan.states(), strict=True):
            mi = keyframe.move_index if keyframe.move_index >= 0 else None
            if keyframe.start_frame != frame:
                out.append(_err(ViolationCode.KEYFRAME_TIMING, "Keyframes must be contiguous.", mi))
            frame = keyframe.end_frame
            if keyframe.contacts != state:
                out.append(
                    _err(ViolationCode.CONTACTS_MISMATCH, "Contacts differ from the beta.", mi)
                )
            c = keyframe.camera.center
            if not (0 <= c.x <= spec.image.width and 0 <= c.y <= spec.image.height):
                out.append(
                    _err(
                        ViolationCode.CAMERA_OUT_OF_FRAME, "Camera centre is outside the image.", mi
                    )
                )
            for ref in _annotation_hold_refs(keyframe.annotations):
                if ref not in holds:
                    out.append(
                        _err(
                            ViolationCode.UNKNOWN_SPEC_HOLD,
                            f"Annotation references hold {ref}.",
                            mi,
                        )
                    )
            points: dict[Limb, Point | None] = {}
            for limb, hold_id in keyframe.contacts.items():
                points[limb] = holds.get(hold_id) if hold_id is not None else None
            ratio = max_reach_ratio(keyframe.hip, points, spec.body)
            if ratio > self.reach_tolerance:
                out.append(
                    _err(
                        ViolationCode.HIP_UNREACHABLE,
                        f"Hip at ({keyframe.hip.x:.0f}, {keyframe.hip.y:.0f}) leaves a limb at {ratio:.0%} "
                        "of its length; move the hip closer to the contacts or omit it to auto-place.",
                        mi,
                    )
                )
        if frame > spec.meta.duration_frames:
            out.append(
                _err(ViolationCode.KEYFRAME_TIMING, "Keyframes run past the video duration.")
            )

        expected_chapters = [(k.move_index, k.start_frame) for k in spec.keyframes[1:]]
        actual_chapters = [(c.move_index, c.start_frame) for c in spec.chapters]
        if expected_chapters != actual_chapters:
            out.append(
                _err(
                    ViolationCode.CHAPTER_MISMATCH,
                    "There must be one chapter per move, at its start.",
                )
            )
        return out


def _annotation_hold_refs(annotations: Iterable[object]) -> list[int]:
    refs: list[int] = []
    for a in annotations:
        if isinstance(a, HoldHighlight):
            refs.append(a.hold_id)
        elif isinstance(a, MoveArrow):
            refs.append(a.to_hold_id)
            if a.from_hold_id is not None:
                refs.append(a.from_hold_id)
        elif isinstance(a, Callout) and a.hold_id is not None:
            refs.append(a.hold_id)
    return refs
