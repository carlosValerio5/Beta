from __future__ import annotations

import base64
import json

import pytest
from pydantic import BaseModel

from beta_core.errors import AdapterError
from beta_llm.claude import StructuredCaller, image_block
from beta_llm.prompts import Prompt
from beta_llm.transport import ScriptedTransport, TransportResponse

from beta_core.testing import FAKE_IMAGE as IMAGE


class Answer(BaseModel):
    move: int
    why: str


PROMPT = Prompt(
    name="t",
    version=1,
    model="claude-opus-5-5",
    effort="high",
    max_tokens=2000,
    system="SYSTEM",
    user_template="USER $x",
)


def test_builds_cached_structured_request() -> None:
    transport = ScriptedTransport(json.dumps({"move": 3, "why": "closest"}))
    result = StructuredCaller(transport).call(PROMPT, user_text="hello", images=[IMAGE], output=Answer)

    params, fallbacks = transport.calls[0]
    assert fallbacks is True
    assert params["model"] == "claude-opus-5-5"
    assert params["max_tokens"] == 2000
    assert params["system"] == [{"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}]
    assert params["output_config"]["effort"] == "high"
    assert params["output_config"]["format"]["type"] == "json_schema"
    content = params["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[-1] == {"type": "text", "text": "hello"}
    assert "thinking" not in params
    assert result.value == Answer(move=3, why="closest")
    assert result.prompt_ref == "t@v1"


def test_model_override_disables_fallback_for_haiku() -> None:
    transport = ScriptedTransport('{"move": 1, "why": "x"}')
    StructuredCaller(transport, model_override="claude-haiku-5-5").call(PROMPT, user_text="u", output=Answer)
    params, fallbacks = transport.calls[0]
    assert params["model"] == "claude-haiku-5-5"
    assert fallbacks is False


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_unusable_stop_reasons(stop_reason: str) -> None:
    transport = ScriptedTransport(TransportResponse(text="{}", model="m", stop_reason=stop_reason))
    with pytest.raises(AdapterError, match=stop_reason):
        StructuredCaller(transport).call(PROMPT, user_text="u", output=Answer)


def test_invalid_json_is_adapter_error() -> None:
    transport = ScriptedTransport('{"move": "not-a-number"}')
    with pytest.raises(AdapterError, match="schema"):
        StructuredCaller(transport).call(PROMPT, user_text="u", output=Answer)


def test_missing_text_is_adapter_error() -> None:
    transport = ScriptedTransport(TransportResponse(text=None, model="m", stop_reason="end_turn"))
    with pytest.raises(AdapterError, match="no text"):
        StructuredCaller(transport).call(PROMPT, user_text="u", output=Answer)


def test_image_block_is_base64_jpeg() -> None:
    block = image_block(IMAGE)
    assert block["source"]["media_type"] == "image/jpeg"
    assert base64.b64decode(block["source"]["data"]) == IMAGE.data
