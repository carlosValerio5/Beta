"""Deterministic offline planner and director (no API key needed).

They keep the whole product usable in development, CI and evals, and give Claude a baseline to
beat. The planner climbs greedily: move the lower hand to the highest hold it can reach from a
comfortable body position; when no hand can progress, bring the lower foot up; finish by matching.
Reachability uses the same kinematics as the validator, with a stricter limit so heuristic betas
always validate.
"""

from __future__ import annotations

from beta_core.choreography import assemble_motion_spec
from beta_core.domain.beta import BetaPlan, Contacts, Limb, Move, Provenance, Technique
from beta_core.domain.climber import BodyModel, ClimbingStyle
from beta_core.domain.geometry import Point
from beta_core.domain.grades import Grade
from beta_core.domain.holds import HoldType, Problem
from beta_core.domain.motion import Easing, MotionDraft, MotionSpec, MoveDirection
from beta_core.kinematics import best_hip
from beta_core.ports import BetaRequest, MotionRequest

REACH_LIMIT = 1.0  # validator allows 1.08
STRETCH = 0.95  # above this a hand move is a deadpoint (dynamic) or lock-off (static)
MIN_PROGRESS_PX = 20.0
MAX_MOVES = 40


class _Climb:
    """Search state for one plan: hold centres, body in pixels, memoised reach ratios."""

    def __init__(self, problem: Problem, body_px: BodyModel) -> None:
        self.problem = problem
        self.body = body_px
        self.centers: dict[int, Point] = {h.id: h.center for h in problem.holds}
        self._cache: dict[tuple[int | None, ...], tuple[Point, float]] = {}

    def pose(self, contacts: Contacts) -> tuple[Point, float]:
        key = (contacts.lh, contacts.rh, contacts.lf, contacts.rf)
        if key not in self._cache:
            points = {
                limb: self.centers[h] if h is not None else None for limb, h in contacts.items()
            }
            self._cache[key] = best_hip(points, self.body)
        return self._cache[key]

    def ratio(self, contacts: Contacts) -> float:
        return self.pose(contacts)[1]

    def y(self, hold_id: int | None) -> float:
        return self.centers[hold_id].y if hold_id is not None else float("inf")

    def x(self, hold_id: int) -> float:
        return self.centers[hold_id].x

    def by_height(self, ids: list[int]) -> list[int]:
        return sorted(ids, key=lambda h: (self.y(h), self.x(h)))


class HeuristicBetaPlanner:
    name = "heuristic-planner@1"

    def plan(self, request: BetaRequest) -> BetaPlan:
        problem = request.problem
        climb = _Climb(problem, request.body.scaled(request.px_per_cm))
        contacts = self._start(climb)
        dynamic = request.profile.style is ClimbingStyle.DYNAMIC

        moves: list[Move] = []
        ratios: list[float] = []
        top = problem.top_hold_id
        while len(moves) < MAX_MOVES and not (contacts.lh == contacts.rh == top):
            step = self._hand_move(climb, contacts) or self._foot_move(climb, contacts)
            if step is None:
                break
            limb, hold = step
            after = contacts.with_contact(limb, hold)
            technique = self._technique(climb, contacts, after, limb, hold, dynamic)
            moves.append(
                Move(
                    index=len(moves),
                    limb=limb,
                    hold_id=hold,
                    technique=technique,
                    cue=_cue(limb, hold, technique, problem),
                )
            )
            ratios.append(climb.ratio(after))
            contacts = after

        crux = (max(range(len(ratios)), key=ratios.__getitem__),) if ratios else ()
        hardest = max(ratios, default=0.0)
        grade = Grade(v=min(8, 1 + sum(hardest > t for t in (0.8, 0.85, 0.9, 0.95)) + int(dynamic)))
        hands = sum(1 for m in moves if m.limb.is_hand)
        summary = (
            f"{len(moves)} moves ({hands} hand, {len(moves) - hands} foot). Keep your feet high so "
            f"each reach stays short; the hardest move is #{crux[0] + 1}."
            if crux
            else "No sequence found from the start holds."
        )
        return BetaPlan(
            id=request.plan_id,
            analysis_id=request.analysis_id,
            start=self._initial_start,
            moves=tuple(moves),
            crux_move_indices=crux,
            summary=summary,
            grade_estimate=grade,
            confidence=0.35,
            style=request.profile.style,
            provenance=Provenance(planner=self.name),
        )

    # ------------------------------------------------------------------ start

    def _start(self, climb: _Climb) -> Contacts:
        starts = sorted(climb.problem.start_hold_ids, key=climb.x)
        lh, rh = (starts[0], starts[-1])
        hands = Contacts(lh=lh, rh=rh)
        hand_low = max(climb.y(lh), climb.y(rh))
        candidates = climb.by_height(
            [
                h
                for h in climb.centers
                if h not in starts and climb.y(h) > hand_low + climb.body.torso * 0.5
            ]
        )[:8]
        best = hands
        for i, a in enumerate(candidates):
            for b in candidates[i + 1 :]:
                lf, rf = (a, b) if climb.x(a) <= climb.x(b) else (b, a)
                trial = hands.model_copy(update={"lf": lf, "rf": rf})
                if climb.ratio(trial) <= REACH_LIMIT:
                    best = trial
                    break
            if best is not hands:
                break
        self._initial_start = best
        return best

    # ------------------------------------------------------------------ moves

    def _hand_move(self, climb: _Climb, contacts: Contacts) -> tuple[Limb, int] | None:
        top = climb.problem.top_hold_id
        for hand, other in ((Limb.LH, Limb.RH), (Limb.RH, Limb.LH)):
            if contacts.get(other) == top and contacts.get(hand) != top:
                match = contacts.with_contact(hand, top)
                return (hand, top) if climb.ratio(match) <= REACH_LIMIT else None

        order = sorted(Limb.hands(), key=lambda h: (-climb.y(contacts.get(h)), h.value))
        for hand in order:
            current = contacts.get(hand)
            other_hold = contacts.get(Limb.RH if hand is Limb.LH else Limb.LH)
            candidates = climb.by_height(
                [
                    h
                    for h in climb.centers
                    if climb.y(h) < climb.y(current) - MIN_PROGRESS_PX
                    and h != other_hold
                    and climb.problem.hold(h).hold_type is not HoldType.FOOTHOLD
                ]
            )
            for hold in candidates:
                if climb.ratio(contacts.with_contact(hand, hold)) <= REACH_LIMIT:
                    return hand, hold
        return None

    def _foot_move(self, climb: _Climb, contacts: Contacts) -> tuple[Limb, int] | None:
        highest_hand = min(climb.y(contacts.lh), climb.y(contacts.rh))
        floor = highest_hand + climb.body.torso * 0.5
        order = sorted(Limb.feet(), key=lambda f: (-climb.y(contacts.get(f)), f.value))
        for foot in order:
            current = contacts.get(foot)
            other_foot = contacts.get(Limb.RF if foot is Limb.LF else Limb.LF)
            candidates = climb.by_height(
                [
                    h
                    for h in climb.centers
                    if climb.y(h) < climb.y(current) - MIN_PROGRESS_PX
                    and climb.y(h) > floor
                    and h not in (contacts.lh, contacts.rh, other_foot)
                ]
            )
            for hold in candidates:
                if climb.ratio(contacts.with_contact(foot, hold)) <= REACH_LIMIT:
                    return foot, hold
        return None

    @staticmethod
    def _technique(
        climb: _Climb, before: Contacts, after: Contacts, limb: Limb, hold: int, dynamic: bool
    ) -> Technique:
        if not limb.is_hand:
            hip, _ = climb.pose(after)
            return Technique.HIGH_STEP if climb.y(hold) < hip.y else Technique.STEP
        other = before.get(Limb.RH if limb is Limb.LH else Limb.LH)
        if hold == other:
            return Technique.MATCH
        if other is not None:
            crossing = (limb is Limb.LH and climb.x(hold) > climb.x(other) + 15) or (
                limb is Limb.RH and climb.x(hold) < climb.x(other) - 15
            )
            if crossing:
                return Technique.CROSS
        if climb.ratio(after) > STRETCH:
            return Technique.DEADPOINT if dynamic else Technique.LOCK_OFF
        return Technique.REACH


def _cue(limb: Limb, hold: int, technique: Technique, problem: Problem) -> str:  # noqa: PLR0911
    who = limb.label
    kind = problem.hold(hold).hold_type
    grip = {
        HoldType.SLOPER: " (open hand, keep weight under it)",
        HoldType.CRIMP: " (crimp it, thumb over)",
        HoldType.PINCH: " (pinch with the thumb)",
    }.get(kind, "")
    match technique:
        case Technique.MATCH:
            return "Match both hands on the top"
        case Technique.CROSS:
            return f"Cross {who.lower()} over to hold {hold}"
        case Technique.DEADPOINT:
            return f"Drive from the feet and deadpoint to hold {hold}"
        case Technique.LOCK_OFF:
            return f"Lock off and reach {who.lower()} to hold {hold}{grip}"
        case Technique.HIGH_STEP:
            return f"High step {who.lower()} onto hold {hold}"
        case Technique.STEP:
            return f"{who} up to hold {hold}"
        case _:
            return f"{who} to hold {hold}{grip}"


class ChoreographyDirector:
    """Rule-based pacing: long opening, quick feet, snappy dynamics, slow-motion crux."""

    name = "choreography-director@1"

    def direct(self, request: MotionRequest) -> MotionSpec:
        plan = request.beta
        crux = set(plan.crux_move_indices)
        opening = plan.summary.split(". ")[0].strip()
        directions = [
            MoveDirection(move_index=-1, duration_s=2.0, caption=opening or "Start position")
        ]
        for move in plan.moves:
            dynamic = move.technique.is_dynamic
            if move.index in crux:
                direction = MoveDirection(
                    move_index=move.index,
                    duration_s=1.4,
                    slow_motion=True,
                    show_trail=True,
                    easing=Easing.SNAP if dynamic else Easing.EASE_IN_OUT,
                    callout=f"Crux · {move.technique.label}",
                )
            elif dynamic:
                direction = MoveDirection(
                    move_index=move.index, duration_s=0.8, easing=Easing.SNAP, show_trail=True
                )
            elif not move.limb.is_hand:
                direction = MoveDirection(
                    move_index=move.index, duration_s=0.8, easing=Easing.EASE_OUT
                )
            elif move.technique is Technique.MATCH:
                direction = MoveDirection(
                    move_index=move.index, duration_s=1.0, caption="Match and top out!"
                )
            else:
                direction = MoveDirection(move_index=move.index, duration_s=1.2)
            directions.append(direction)
        return assemble_motion_spec(
            MotionDraft(directions=directions),
            plan=plan,
            problem=request.problem,
            image=request.image_ref,
            body_cm=request.body,
            px_per_cm=request.px_per_cm,
            provenance=Provenance(planner=self.name),
        )
