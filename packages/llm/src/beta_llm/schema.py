"""Turn a Pydantic model's JSON Schema into one accepted by Claude structured outputs.

Structured outputs need closed objects (``additionalProperties: false``) with every property listed
in ``required``; optional values are expressed as ``anyOf [..., null]`` (Pydantic already does this
for ``X | None``). Validation keywords the API does not enforce are dropped — Pydantic re-validates
(and the draft models clamp) when the answer comes back.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

UNSUPPORTED_KEYWORDS = frozenset(
    {
        "default",
        "title",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
    }
)


def _fix(node: Any) -> Any:
    if isinstance(node, list):
        return [_fix(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in UNSUPPORTED_KEYWORDS:
            continue
        if key in ("properties", "$defs"):
            out[key] = {name: _fix(sub) for name, sub in value.items()}
        else:
            out[key] = _fix(value)
    if out.get("type") == "object" and "properties" in out:
        out["additionalProperties"] = False
        out["required"] = list(out["properties"])
    return out


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    fixed: dict[str, Any] = _fix(copy.deepcopy(model.model_json_schema()))
    return fixed
