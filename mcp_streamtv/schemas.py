"""Portable MCP input schemas (§7.4)."""

from __future__ import annotations

from typing import Any


def normalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Collapse anyOf-null, drop $ref, require type+description on properties."""
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}

    def _walk(node: Any) -> Any:
        if isinstance(node, list):
            return [_walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        out = dict(node)
        if "anyOf" in out or "oneOf" in out or "allOf" in out:
            variants = out.get("anyOf") or out.get("oneOf") or out.get("allOf") or []
            non_null = [v for v in variants if not (isinstance(v, dict) and v.get("type") == "null")]
            if len(non_null) == 1 and isinstance(non_null[0], dict):
                merged = dict(non_null[0])
                for k, v in out.items():
                    if k not in ("anyOf", "oneOf", "allOf"):
                        merged.setdefault(k, v)
                out = merged
            else:
                out.pop("anyOf", None)
                out.pop("oneOf", None)
                out.pop("allOf", None)
                out.setdefault("type", "object")
        out.pop("$ref", None)
        out.pop("$defs", None)
        out.pop("definitions", None)
        if out.get("additionalProperties") is True:
            out["additionalProperties"] = False
        if "properties" in out and isinstance(out["properties"], dict):
            props = {}
            for key, val in out["properties"].items():
                prop = _walk(val) if isinstance(val, dict) else {"type": "string"}
                if isinstance(prop, dict):
                    prop.setdefault("type", "string")
                    prop.setdefault("description", key)
                props[key] = prop
            out["properties"] = props
            if "required" in out and isinstance(out["required"], list):
                # Drop required entries that have defaults / are optional after collapse
                out["required"] = [
                    r for r in out["required"] if r in props and "default" not in props[r]
                ]
        return out

    root = _walk(schema)
    if not isinstance(root, dict):
        return {"type": "object", "properties": {}}
    root.setdefault("type", "object")
    root.setdefault("properties", {})
    return root


def schema_is_portable(schema: dict[str, Any]) -> tuple[bool, str]:
    raw = str(schema)

    def _bad(node: Any) -> str | None:
        if isinstance(node, list):
            for x in node:
                msg = _bad(x)
                if msg:
                    return msg
            return None
        if not isinstance(node, dict):
            return None
        for k in ("anyOf", "oneOf", "allOf", "$ref"):
            if k in node:
                return f"contains {k}"
        if node.get("additionalProperties") is True:
            return "additionalProperties true"
        if "properties" in node:
            for key, val in (node.get("properties") or {}).items():
                if not isinstance(val, dict):
                    return f"property {key} not object"
                if "type" not in val:
                    return f"property {key} missing type"
                if "description" not in val:
                    return f"property {key} missing description"
                msg = _bad(val)
                if msg:
                    return msg
        return None

    if schema.get("type") != "object":
        return False, "root type not object"
    msg = _bad(schema)
    if msg:
        return False, msg
    return True, "ok"


def schema_from_signature(fn: Any) -> dict[str, Any]:
    """Best-effort JSON schema from a callable signature."""
    import inspect

    props: dict[str, Any] = {}
    required: list[str] = []
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return {"type": "object", "properties": {}}
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        ann = param.annotation
        typ = "string"
        ann_s = str(ann)
        if ann is int or "int" in ann_s:
            typ = "integer"
        elif ann is bool or "bool" in ann_s:
            typ = "boolean"
        elif ann is float or "float" in ann_s:
            typ = "number"
        elif "list" in ann_s.lower() or "List" in ann_s:
            typ = "array"
        props[name] = {"type": typ, "description": name}
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            props[name]["default"] = param.default if param.default is not None else None
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return normalize_schema(schema)
