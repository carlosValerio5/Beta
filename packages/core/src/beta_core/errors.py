"""Domain error hierarchy. Adapters wrap third-party failures in :class:`AdapterError`."""

from __future__ import annotations


class BetaError(Exception):
    """Base class for every error raised by Beta Climbing code."""


class NotFoundError(BetaError):
    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} {entity_id!r} not found")
        self.entity = entity
        self.entity_id = entity_id


class UnknownHoldError(NotFoundError):
    def __init__(self, hold_id: int) -> None:
        super().__init__("hold", str(hold_id))
        self.hold_id = hold_id


class InvalidStateError(BetaError):
    """The operation is not allowed in the entity's current state."""


class AdapterError(BetaError):
    """A port implementation failed (network, subprocess, third-party SDK)."""
