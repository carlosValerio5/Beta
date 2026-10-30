from __future__ import annotations

from typing import Any

from beta_core.domain.beta import BetaDraft
from beta_core.domain.motion import MotionDraft
from beta_llm.schema import strict_schema


def walk(node: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(node, dict):
        out.append(node)
        for value in node.values():
            out.extend(walk(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(walk(value))
    return out


def test_objects_are_closed_and_fully_required() -> None:
    schema = strict_schema(BetaDraft)
    objects = [n for n in walk(schema) if n.get("type") == "object" and "properties" in n]
    assert objects
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_unsupported_keywords_are_stripped() -> None:
    schema = strict_schema(MotionDraft)
    banned = {"default", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength"}
    for node in walk(schema):
        assert not banned & set(node), node


def test_refs_and_descriptions_survive() -> None:
    schema = strict_schema(BetaDraft)
    assert "$defs" in schema
    assert any("$ref" in n for n in walk(schema))
    assert "description" in schema["properties"]["moves"]
