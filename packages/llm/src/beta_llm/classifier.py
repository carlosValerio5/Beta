"""``HoldClassifier`` backed by Claude Haiku (prompt: ``prompts/hold_classifier``)."""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic import Field

from beta_core.domain.base import DraftModel
from beta_core.domain.holds import Hold, HoldType
from beta_core.ports import MarkRenderer, NormalizedImage
from beta_llm.claude import StructuredCaller
from beta_llm.prompts import PromptRegistry
from beta_llm.transport import Transport


class HoldTypeGuess(DraftModel):
    id: int
    hold_type: HoldType


class HoldTypeDraft(DraftModel):
    holds: list[HoldTypeGuess] = Field(default_factory=list)


class ClaudeHoldClassifier:
    def __init__(
        self,
        transport: Transport,
        registry: PromptRegistry,
        marks: MarkRenderer,
        *,
        prompt_version: int | None = None,
        model_override: str | None = None,
    ) -> None:
        self._caller = StructuredCaller(transport, model_override=model_override)
        self._registry = registry
        self._marks = marks
        self._prompt_version = prompt_version

    def classify(self, image: NormalizedImage, holds: Sequence[Hold]) -> list[Hold]:
        if not holds:
            return []
        prompt = self._registry.get("hold_classifier", self._prompt_version)
        user = prompt.render_user(
            hold_ids=", ".join(str(h.id) for h in holds),
            guesses=json.dumps({str(h.id): h.hold_type.value for h in holds}),
        )
        marked = self._marks.render_marks(image, holds)
        result = self._caller.call(prompt, user_text=user, images=[marked], output=HoldTypeDraft)
        types = {g.id: g.hold_type for g in result.value.holds}
        return [
            h.model_copy(update={"hold_type": types[h.id]}) if h.id in types else h for h in holds
        ]
