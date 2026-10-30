"""Domain events: the append-only record that lands in the bronze layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import Field

from beta_core.domain.base import DomainModel

EVENT_SCHEMA_VERSION = 1


class EventName(StrEnum):
    IMAGE_INGESTED = "image.ingested"
    HOLDS_DETECTED = "holds.detected"
    PROBLEM_SELECTED = "problem.selected"
    BETA_GENERATED = "beta.generated"
    BETA_FAILED = "beta.failed"
    VIDEO_DIRECTED = "video.directed"
    VIDEO_RENDERED = "video.rendered"
    VIDEO_FAILED = "video.failed"
    FEEDBACK_RECORDED = "feedback.recorded"
    PLAYBACK_RECORDED = "playback.recorded"


class DomainEvent(DomainModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    name: EventName
    occurred_at: datetime
    entity_id: str
    schema_version: int = EVENT_SCHEMA_VERSION
    payload: dict[str, Any]
