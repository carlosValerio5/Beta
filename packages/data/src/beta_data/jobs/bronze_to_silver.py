"""Bronze → silver: normalise and dedupe images, explode events into typed tables."""

from __future__ import annotations

from typing import Any

from beta_core.domain.beta import BetaPlan
from beta_core.domain.events import DomainEvent, EventName
from beta_core.domain.motion import Caption, MotionSpec
from beta_core.ports import ImagePreprocessor
from beta_data.bronze import event_files, read_events
from beta_data.contracts import contract
from beta_data.layout import Lakehouse
from beta_data.lineage import RunManifest
from beta_data.tables import write_table
from beta_vision.preprocess import PillowPreprocessor, hamming

JOB = "bronze_to_silver"
DUPLICATE_HAMMING = 4


def run(lake: Lakehouse, preprocessor: ImagePreprocessor | None = None) -> RunManifest:
    manifest = RunManifest.start(JOB)
    events = list(read_events(lake))
    for path in event_files(lake):
        manifest.add_input(lake, path)

    tables: dict[str, list[dict[str, Any]]] = {
        "images": _images(lake, events, preprocessor or PillowPreprocessor(), manifest),
        "holds": _holds(events),
        "problems": _problems(events),
        **_betas(events),
        **_videos(events),
        "feedback": _feedback(events),
    }
    for name, rows in tables.items():
        c = contract(name)
        path = write_table(lake, c, rows)
        manifest.add_output(lake, name, path, len(rows), c.version)
    return manifest.finish(lake)


def _latest(events: list[DomainEvent], *names: EventName) -> dict[str, DomainEvent]:
    """Last event per entity among ``names`` (later events supersede earlier ones)."""
    latest: dict[str, DomainEvent] = {}
    for e in events:
        if e.name in names:
            latest[e.entity_id] = e
    return latest


def _images(
    lake: Lakehouse, events: list[DomainEvent], pre: ImagePreprocessor, manifest: RunManifest
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: list[tuple[str, str]] = []  # (image_sha256, dhash) in ingest order
    for e in events:
        if e.name is not EventName.IMAGE_INGESTED:
            continue
        p = e.payload
        raw_path = lake.root / p["raw_key"]
        manifest.add_input(lake, raw_path)
        image = pre.normalize(raw_path.read_bytes())
        target = lake.silver_image(image.sha256)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(image.data)
        duplicate_of = next(
            (
                sha
                for sha, dh in seen
                if sha == image.sha256 or hamming(dh, image.dhash) <= DUPLICATE_HAMMING
            ),
            None,
        )
        seen.append((image.sha256, image.dhash))
        rows.append(
            {
                "image_sha256": image.sha256,
                "source_sha256": p["raw_sha256"],
                "analysis_id": e.entity_id,
                "device_id": p["device_id"],
                "width": image.width,
                "height": image.height,
                "dhash": image.dhash,
                "gps_stripped": p["gps_stripped"],
                "duplicate_of": duplicate_of,
                "ingested_at": e.occurred_at,
            }
        )
    return rows


def _holds(events: list[DomainEvent]) -> list[dict[str, Any]]:
    rows = []
    for analysis_id, e in _latest(events, EventName.HOLDS_DETECTED).items():
        for h in e.payload["holds"]:
            box = h["bbox"]
            rows.append(
                {
                    "analysis_id": analysis_id,
                    "hold_id": h["id"],
                    "x": box["x"],
                    "y": box["y"],
                    "w": box["w"],
                    "h": box["h"],
                    "color": h["color"],
                    "hold_type": h["hold_type"],
                    "confidence": h["confidence"],
                    "detector": e.payload["detector"],
                }
            )
    return rows


def _problems(events: list[DomainEvent]) -> list[dict[str, Any]]:
    rows = []
    for analysis_id, e in _latest(events, EventName.PROBLEM_SELECTED).items():
        problem = e.payload["problem"]
        rows.append(
            {
                "analysis_id": analysis_id,
                "color": problem["color"],
                "start_hold_ids": problem["start_hold_ids"],
                "top_hold_id": problem["top_hold_id"],
                "hold_ids": sorted(h["id"] for h in problem["holds"]),
                "selected_at": e.occurred_at,
            }
        )
    return rows


def _betas(events: list[DomainEvent]) -> dict[str, list[dict[str, Any]]]:
    betas: list[dict[str, Any]] = []
    moves: list[dict[str, Any]] = []
    for beta_id, e in _latest(events, EventName.BETA_GENERATED, EventName.BETA_FAILED).items():
        p = e.payload
        if e.name is EventName.BETA_GENERATED:
            plan = BetaPlan.model_validate(p["plan"])
            profile = p["profile"]
            crux = set(plan.crux_move_indices)
            betas.append(
                {
                    "beta_id": beta_id,
                    "analysis_id": p["analysis_id"],
                    "status": "ready",
                    "planner": plan.provenance.planner,
                    "prompt": plan.provenance.prompt,
                    "model": plan.provenance.model,
                    "n_moves": len(plan.moves),
                    "grade_v": plan.grade_estimate.v if plan.grade_estimate else None,
                    "confidence": plan.confidence,
                    "style": plan.style.value,
                    "attempts": p["attempts"],
                    "height_cm": profile["height_cm"],
                    "ape_index_cm": profile["ape_index_cm"],
                    "error": None,
                    "created_at": e.occurred_at,
                }
            )
            moves.extend(
                {
                    "beta_id": beta_id,
                    "move_index": m.index,
                    "limb": m.limb.value,
                    "hold_id": m.hold_id,
                    "technique": m.technique.value,
                    "cue": m.cue,
                    "is_crux": m.index in crux,
                }
                for m in plan.moves
            )
        else:
            betas.append(
                {
                    "beta_id": beta_id,
                    "analysis_id": p["analysis_id"],
                    "status": "failed",
                    "planner": None,
                    "prompt": None,
                    "model": None,
                    "n_moves": 0,
                    "grade_v": None,
                    "confidence": None,
                    "style": None,
                    "attempts": p["attempts"],
                    "height_cm": None,
                    "ape_index_cm": None,
                    "error": p["error"],
                    "created_at": e.occurred_at,
                }
            )
    return {"betas": betas, "moves": moves}


def _videos(events: list[DomainEvent]) -> dict[str, list[dict[str, Any]]]:
    specs: list[dict[str, Any]] = []
    keyframes: list[dict[str, Any]] = []
    renders: list[dict[str, Any]] = []
    for video_id, e in _latest(events, EventName.VIDEO_DIRECTED).items():
        spec = MotionSpec.model_validate(e.payload["spec"])
        specs.append(
            {
                "video_id": video_id,
                "beta_id": e.payload["beta_id"],
                "director": spec.provenance.planner,
                "prompt": spec.provenance.prompt,
                "model": spec.provenance.model,
                "fps": spec.meta.fps,
                "duration_frames": spec.meta.duration_frames,
                "n_keyframes": len(spec.keyframes),
                "n_captions": sum(
                    isinstance(a, Caption) for k in spec.keyframes for a in k.annotations
                ),
                "n_slow_motion": sum(k.slow_motion for k in spec.keyframes),
                "attempts": e.payload["attempts"],
                "directed_at": e.occurred_at,
            }
        )
        keyframes.extend(
            {
                "video_id": video_id,
                "move_index": k.move_index,
                "start_frame": k.start_frame,
                "duration_frames": k.duration_frames,
                "hip_x": k.hip.x,
                "hip_y": k.hip.y,
                "camera_x": k.camera.center.x,
                "camera_y": k.camera.center.y,
                "zoom": k.camera.zoom,
                "easing": k.easing.value,
                "slow_motion": k.slow_motion,
                "n_annotations": len(k.annotations),
            }
            for k in spec.keyframes
        )
    for video_id, e in _latest(events, EventName.VIDEO_RENDERED, EventName.VIDEO_FAILED).items():
        rendered = e.name is EventName.VIDEO_RENDERED
        renders.append(
            {
                "video_id": video_id,
                "beta_id": e.payload["beta_id"],
                "status": "ready" if rendered else "failed",
                "duration_s": e.payload.get("duration_s") if rendered else None,
                "error": None if rendered else e.payload.get("error"),
                "at": e.occurred_at,
            }
        )
    return {"motion_specs": specs, "keyframes": keyframes, "renders": renders}


def _feedback(events: list[DomainEvent]) -> list[dict[str, Any]]:
    rows = []
    for e in events:
        if e.name in (EventName.FEEDBACK_RECORDED, EventName.PLAYBACK_RECORDED):
            p = e.payload
            rows.append(
                {
                    "feedback_id": p["id"],
                    "beta_id": p["beta_id"],
                    "kind": p["kind"],
                    "move_index": p["move_index"],
                    "note": p["note"],
                    "created_at": e.occurred_at,
                }
            )
    return rows
