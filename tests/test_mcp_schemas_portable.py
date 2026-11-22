"""Portable MCP schemas (§7.4)."""

from __future__ import annotations

from mcp_streamtv.main import _active_specs, _tool_input_schema
from mcp_streamtv.schemas import normalize_schema, schema_is_portable


def test_normalize_collapses_anyof_null() -> None:
    raw = {
        "type": "object",
        "properties": {
            "x": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "x",
            }
        },
        "required": ["x"],
    }
    out = normalize_schema(raw)
    ok, msg = schema_is_portable(out)
    assert ok, msg
    assert out["properties"]["x"]["type"] == "string"


def test_full_profile_schemas_portable() -> None:
    for name, _desc in _active_specs("full"):
        schema = _tool_input_schema(name)
        ok, msg = schema_is_portable(schema)
        assert ok, f"{name}: {msg}"
        assert schema.get("type") == "object"
