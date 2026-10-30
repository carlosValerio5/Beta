"""One structured Claude call: cached system prompt, images, JSON-schema output (ADR-0005).

Claude Opus 5.5 rejects forced ``tool_choice``, so answers are constrained with structured outputs
(``output_config.format``) instead of a forced tool. Thinking is left at its adaptive default and
depth is set through ``output_config.effort`` from the prompt's front matter.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from beta_core.errors import AdapterError
from beta_core.ports import NormalizedImage
from beta_llm.prompts import Prompt
from beta_llm.schema import strict_schema
from beta_llm.transport import Transport, supports_server_fallback

UNUSABLE_STOP_REASONS = frozenset({"refusal", "max_tokens"})


@dataclass(frozen=True)
class CallResult[M: BaseModel]:
    value: M
    prompt_ref: str
    model: str
    request_id: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


def image_block(image: NormalizedImage) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image.content_type,
            "data": base64.standard_b64encode(image.data).decode("ascii"),
        },
    }


class StructuredCaller:
    def __init__(self, transport: Transport, *, model_override: str | None = None) -> None:
        self._transport = transport
        self._model_override = model_override

    def call[M: BaseModel](
        self,
        prompt: Prompt,
        *,
        user_text: str,
        output: type[M],
        images: Sequence[NormalizedImage] = (),
    ) -> CallResult[M]:
        model = self._model_override or prompt.model
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": prompt.max_tokens,
            "system": [
                {"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        *(image_block(i) for i in images),
                        {"type": "text", "text": user_text},
                    ],
                }
            ],
            "output_config": {
                "effort": prompt.effort,
                "format": {"type": "json_schema", "schema": strict_schema(output)},
            },
        }
        response = self._transport.send(params, fallbacks=supports_server_fallback(model))
        if response.stop_reason in UNUSABLE_STOP_REASONS:
            raise AdapterError(f"{prompt.ref}: model stopped with {response.stop_reason}")
        if response.text is None:
            raise AdapterError(f"{prompt.ref}: model returned no text block")
        try:
            value = output.model_validate_json(response.text)
        except ValidationError as exc:
            raise AdapterError(
                f"{prompt.ref}: output did not match the {output.__name__} schema "
                f"({exc.error_count()} errors)"
            ) from exc
        return CallResult(
            value=value,
            prompt_ref=prompt.ref,
            model=response.model,
            request_id=response.request_id,
            usage=response.usage,
        )
