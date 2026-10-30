from __future__ import annotations

from enum import StrEnum

from beta_core.domain.base import DomainModel


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ViolationCode(StrEnum):
    # BetaPlan
    EMPTY_BETA = "empty_beta"
    MOVE_INDEX_SEQUENCE = "move_index_sequence"
    UNKNOWN_HOLD = "unknown_hold"
    START_HANDS_MISSING = "start_hands_missing"
    START_NOT_ON_START_HOLDS = "start_not_on_start_holds"
    NOT_FINISHED = "not_finished"
    NO_OP_MOVE = "no_op_move"
    UNREACHABLE = "unreachable"
    CRUX_INDEX_OUT_OF_RANGE = "crux_index_out_of_range"
    # MotionSpec
    KEYFRAME_SEQUENCE = "keyframe_sequence"
    KEYFRAME_TIMING = "keyframe_timing"
    CONTACTS_MISMATCH = "contacts_mismatch"
    HIP_UNREACHABLE = "hip_unreachable"
    CAMERA_OUT_OF_FRAME = "camera_out_of_frame"
    UNKNOWN_SPEC_HOLD = "unknown_spec_hold"
    CHAPTER_MISMATCH = "chapter_mismatch"


class Violation(DomainModel):
    code: ViolationCode
    message: str
    move_index: int | None = None
    severity: Severity = Severity.ERROR
