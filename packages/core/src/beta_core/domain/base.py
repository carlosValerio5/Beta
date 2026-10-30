from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Immutable, strict base for domain types. Change with ``model_copy(update=...)``."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DraftModel(BaseModel):
    """Base for LLM-facing drafts: tolerant of extra keys, converted to domain types in code."""

    model_config = ConfigDict(extra="ignore")
