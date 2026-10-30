from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from beta_core.errors import AdapterError
from beta_llm.transport import (
    FALLBACK_BETA,
    AnthropicTransport,
    CassetteTransport,
    ScriptedTransport,
    TransportResponse,
    supports_server_fallback,
)

PARAMS: dict[str, Any] = {
    "model": "claude-opus-5-5",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "hi"}],
}


def sdk_message(text: str = '{"ok": true}') -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        model="claude-opus-5-5",
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=7,
        ),
        _request_id="req_1",
    )


class FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def fake_client(result: Any) -> SimpleNamespace:
    return SimpleNamespace(
        messages=FakeMessages(result), beta=SimpleNamespace(messages=FakeMessages(result))
    )


def test_anthropic_transport_uses_beta_fallbacks() -> None:
    client = fake_client(sdk_message())
    out = AnthropicTransport(client).send(PARAMS, fallbacks=True)
    call = client.beta.messages.calls[0]
    assert call["betas"] == [FALLBACK_BETA]
    assert call["extra_body"] == {"fallbacks": "default"}
    assert out.text == '{"ok": true}'
    assert out.usage["cache_creation_input_tokens"] == 7
    assert out.request_id == "req_1"
    assert not client.messages.calls


def test_anthropic_transport_plain_without_fallbacks() -> None:
    client = fake_client(sdk_message())
    AnthropicTransport(client).send(PARAMS, fallbacks=False)
    assert client.messages.calls
    assert "fallbacks" not in client.messages.calls[0]


def test_anthropic_transport_wraps_sdk_errors() -> None:
    err = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    with pytest.raises(AdapterError, match="connection"):
        AnthropicTransport(fake_client(err)).send(PARAMS, fallbacks=False)


@pytest.mark.parametrize(
    ("model", "expected"),
    [("claude-opus-5-5", True), ("claude-sonnet-5-5", True), ("claude-haiku-5-5", False)],
)
def test_supports_server_fallback(model: str, expected: bool) -> None:
    assert supports_server_fallback(model) is expected


def test_scripted_transport_records_calls() -> None:
    transport = ScriptedTransport('{"a": 1}')
    out = transport.send(PARAMS, fallbacks=True)
    assert out.text == '{"a": 1}'
    assert transport.calls == [(PARAMS, True)]


def test_cassette_records_then_replays(tmp_path: Path) -> None:
    inner = ScriptedTransport(
        TransportResponse(text="recorded", model="claude-opus-5-5", stop_reason="end_turn")
    )
    recorder = CassetteTransport(tmp_path, inner=inner)
    first = recorder.send(PARAMS, fallbacks=True)
    assert len(list(tmp_path.glob("*.json"))) == 1

    replay = CassetteTransport(tmp_path)
    assert replay.send(PARAMS, fallbacks=True) == first


def test_cassette_miss_in_replay_mode(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match="cassette"):
        CassetteTransport(tmp_path).send(PARAMS, fallbacks=False)


def test_real_sdk_serialises_fallbacks_and_structured_output() -> None:
    """Characterisation test: what actually goes over the wire through the installed SDK."""
    import json as _json

    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = _json.loads(request.content)
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": '{"ok": true}'}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        )

    client = anthropic.Anthropic(
        api_key="test-key",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    params = {
        **PARAMS,
        "system": [{"type": "text", "text": "S", "cache_control": {"type": "ephemeral"}}],
        "output_config": {
            "effort": "high",
            "format": {"type": "json_schema", "schema": {"type": "object"}},
        },
    }
    out = AnthropicTransport(client).send(params, fallbacks=True)

    assert out.text == '{"ok": true}'
    assert seen["body"]["fallbacks"] == "default"
    assert seen["body"]["output_config"]["effort"] == "high"
    assert seen["body"]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert FALLBACK_BETA in seen["headers"]["anthropic-beta"]
