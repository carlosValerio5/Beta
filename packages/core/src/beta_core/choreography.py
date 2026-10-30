"""Turn a director's :class:`MotionDraft` plus a :class:`BetaPlan` into a :class:`MotionSpec`.

The director controls *how* the beta is shown (timing, easing, hip, camera, text). The beta controls
*what* happens: contacts are copied from ``plan.states()`` so the video cannot contradict the beta.
"""

from __future__ import annotations

from collections.abc import Mapping

from beta_core.domain.beta import BetaPlan, Contacts, Limb, Move, Provenance
from beta_core.domain.climber import BodyModel
from beta_core.domain.geometry import Point
from beta_core.domain.holds import Problem
from beta_core.domain.motion import (
    CALLOUT_MAX,
    CAPTION_MAX,
    Annotation,
    Callout,
    Camera,
    Caption,
    Chapter,
    Easing,
    HoldHighlight,
    ImageRef,
    Keyframe,
    MotionDraft,
    MotionMeta,
    MotionSpec,
    MoveArrow,
    MoveDirection,
    SpecHold,
    Trail,
)
from beta_core.kinematics import contact_points, natural_hip

START_S = 1.6
MOVE_S = 1.2
DYNAMIC_S = 0.8
OUTRO_S = 1.0
SLOW_FACTOR = 1.75
CAMERA_PADDING = 1.6
AUTO_ZOOM_MAX = 2.5


def assemble_motion_spec(
    draft: MotionDraft,
    *,
    plan: BetaPlan,
    problem: Problem,
    image: ImageRef,
    body_cm: BodyModel,
    px_per_cm: float,
    provenance: Provenance,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
) -> MotionSpec:
    body = body_cm.scaled(px_per_cm)
    directions: dict[int, MoveDirection] = {d.move_index: d for d in draft.directions}
    crux = set(plan.crux_move_indices)
    states = plan.states()

    keyframes: list[Keyframe] = []
    chapters: list[Chapter] = []
    frame = 0
    for i, contacts in enumerate(states):
        move_index = i - 1
        move = plan.moves[move_index] if move_index >= 0 else None
        direction = directions.get(move_index)
        slow = direction.slow_motion if direction else move_index in crux
        seconds = direction.duration_s if direction else _default_seconds(move)
        duration = max(1, round(seconds * fps * (SLOW_FACTOR if slow else 1.0)))

        points = contact_points(problem, contacts)
        hip = direction.hip if direction and direction.hip else natural_hip(points, body)
        camera = (
            direction.camera if direction and direction.camera else _auto_camera(points, hip, image)
        )
        if direction:
            easing = direction.easing
        elif move and move.technique.is_dynamic:
            easing = Easing.SNAP
        else:
            easing = Easing.EASE_IN_OUT

        previous = states[i - 1] if i > 0 else None
        keyframes.append(
            Keyframe(
                move_index=move_index,
                start_frame=frame,
                duration_frames=duration,
                contacts=contacts,
                hip=hip,
                limb=move.limb if move else None,
                technique=move.technique if move else None,
                easing=easing,
                camera=camera,
                annotations=_annotations(move, previous, direction, problem, crux),
                slow_motion=slow,
            )
        )
        if move:
            chapters.append(
                Chapter(move_index=move.index, start_frame=frame, title=_chapter_title(move))
            )
        frame += duration

    return MotionSpec(
        beta_id=plan.id,
        meta=MotionMeta(
            fps=fps, width=width, height=height, duration_frames=frame + round(OUTRO_S * fps)
        ),
        image=image,
        px_per_cm=px_per_cm,
        body=body,
        holds=tuple(
            SpecHold(
                id=h.id,
                center=h.center,
                radius=h.size / 2,
                color=h.color,
                role=problem.role_of(h.id),
            )
            for h in problem.holds
        ),
        keyframes=tuple(keyframes),
        chapters=tuple(chapters),
        provenance=provenance,
    )


def _default_seconds(move: Move | None) -> float:
    if move is None:
        return START_S
    return DYNAMIC_S if move.technique.is_dynamic else MOVE_S


def _auto_camera(points: Mapping[Limb, Point | None], hip: Point, image: ImageRef) -> Camera:
    xs = [p.x for p in points.values() if p is not None] + [hip.x]
    ys = [p.y for p in points.values() if p is not None] + [hip.y]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    region_w = max((max_x - min_x) * CAMERA_PADDING, image.width / AUTO_ZOOM_MAX)
    region_h = max((max_y - min_y) * CAMERA_PADDING, image.height / AUTO_ZOOM_MAX)
    zoom = min(image.width / region_w, image.height / region_h, AUTO_ZOOM_MAX)
    center = Point(
        x=min(max((min_x + max_x) / 2, 0.0), float(image.width)),
        y=min(max((min_y + max_y) / 2, 0.0), float(image.height)),
    )
    return Camera(center=center, zoom=max(1.0, zoom))


def _annotations(
    move: Move | None,
    previous: Contacts | None,
    direction: MoveDirection | None,
    problem: Problem,
    crux: set[int],
) -> tuple[Annotation, ...]:
    if move is None:
        out: list[Annotation] = [HoldHighlight(hold_id=h) for h in problem.start_hold_ids]
        out.append(
            Caption(
                text=(direction.caption if direction and direction.caption else "Start position")
            )
        )
        return tuple(out)

    out = [
        HoldHighlight(hold_id=move.hold_id),
        MoveArrow(
            limb=move.limb,
            from_hold_id=previous.get(move.limb) if previous else None,
            to_hold_id=move.hold_id,
        ),
    ]
    caption = (
        direction.caption if direction and direction.caption else move.cue.strip()[:CAPTION_MAX]
    )
    if caption:
        out.append(Caption(text=caption))

    callout_text = direction.callout if direction and direction.callout else None
    if callout_text is None:
        label = move.technique.label.capitalize() if move.technique.is_notable else ""
        if move.index in crux:
            callout_text = f"Crux · {label}" if label else "Crux"
        elif label:
            callout_text = label
    if callout_text:
        out.append(
            Callout(text=callout_text[:CALLOUT_MAX], technique=move.technique, hold_id=move.hold_id)
        )

    if move.technique.is_dynamic or (direction and direction.show_trail):
        out.append(Trail(limb=move.limb))
    return tuple(out)


def _chapter_title(move: Move) -> str:
    return f"{move.index + 1}. {move.limb.label} · {move.technique.label}"
