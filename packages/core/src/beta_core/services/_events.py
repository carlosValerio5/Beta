from __future__ import annotations

from typing import Any

from beta_core.domain.events import DomainEvent, EventName
from beta_core.ports import Clock, EventSink


def emit(
    events: EventSink, clock: Clock, name: EventName, entity_id: str, payload: dict[str, Any]
) -> None:
    events.emit(
        DomainEvent(name=name, occurred_at=clock.now(), entity_id=entity_id, payload=payload)
    )
