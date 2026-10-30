"""The thin seam between our adapters and the Messages API.

``AnthropicTransport`` is the real thing; ``ScriptedTransport`` (tests) and ``CassetteTransport``
(record/replay for evals) let everything above it run without network access.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any, Protocol

import anthropic
from pydantic import BaseModel, ConfigDict, Field

from beta_core.errors import AdapterError

#: Server-side refusal fallback, "default" routing (see docs/agents/README.md).
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_SERVER_FALLBACK_MODELS = frozenset(
    {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
)
_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def supports_server_fallback(model: str) -> bool:
    return model in _SERVER_FALLBACK_MODELS


class TransportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str | None
    model: str
    stop_reason: str | None
    request_id: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class Transport(Protocol):
    def send(self, params: dict[str, Any], *, fallbacks: bool) -> TransportResponse: ...


class AnthropicTransport:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client if client is not None else anthropic.Anthropic()

    def send(self, params: dict[str, Any], *, fallbacks: bool) -> TransportResponse:
        try:
            if fallbacks:
                # The SDK's typed ``fallbacks`` only models the list form; send the "default"
                # routing mode verbatim so the SDK does not try to iterate the string.
                message = self._client.beta.messages.create(
                    **params, betas=[FALLBACK_BETA], extra_body={"fallbacks": "default"}
                )
            else:
                message = self._client.messages.create(**params)
        except anthropic.APIConnectionError as exc:
            raise AdapterError(f"Anthropic API connection failed: {exc}") from exc
        except anthropic.RateLimitError as exc:
            raise AdapterError("Anthropic API rate limit hit after SDK retries") from exc
        except anthropic.APIStatusError as exc:
            raise AdapterError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc

        text = next((b.text for b in message.content if getattr(b, "type", None) == "text"), None)
        usage = {
            field: int(value)
            for field in _USAGE_FIELDS
            if (value := getattr(message.usage, field, None)) is not None
        }
        return TransportResponse(
            text=text,
            model=message.model,
            stop_reason=message.stop_reason,
            request_id=getattr(message, "_request_id", None),
            usage=usage,
        )


class ScriptedTransport:
    """Replays queued responses in order; strings become successful text responses."""

    def __init__(self, *responses: TransportResponse | str | Exception) -> None:
        self._queue: deque[TransportResponse | str | Exception] = deque(responses)
        self.calls: list[tuple[dict[str, Any], bool]] = []

    def send(self, params: dict[str, Any], *, fallbacks: bool) -> TransportResponse:
        self.calls.append((params, fallbacks))
        if not self._queue:
            raise AdapterError("scripted transport has no responses left")
        item = self._queue.popleft()
        if isinstance(item, Exception):
            raise item
        if isinstance(item, str):
            return TransportResponse(
                text=item, model=str(params.get("model", "")), stop_reason="end_turn"
            )
        return item


class CassetteTransport:
    """Record/replay keyed by a hash of the full request. Without ``inner`` it only replays."""

    def __init__(self, directory: Path, inner: Transport | None = None) -> None:
        self.directory = directory
        self.inner = inner

    @staticmethod
    def key(params: dict[str, Any], fallbacks: bool) -> str:
        canonical = json.dumps(
            {"params": params, "fallbacks": fallbacks}, sort_keys=True, default=str
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def send(self, params: dict[str, Any], *, fallbacks: bool) -> TransportResponse:
        key = self.key(params, fallbacks)
        path = self.directory / f"{key}.json"
        if path.is_file():
            return TransportResponse.model_validate_json(path.read_text(encoding="utf-8"))
        if self.inner is None:
            raise AdapterError(
                f"no cassette for request {key[:12]}; record it with a live run first"
            )
        response = self.inner.send(params, fallbacks=fallbacks)
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        return response
