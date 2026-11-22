"""Channel template defaults (§5.0)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PATH = Path(__file__).resolve().parent / "data" / "templates.yaml"

# Example channels used only as templates — never rebuild/reimport on owner server.
TEMPLATE_EXAMPLE_NUMBERS = frozenset(
    {"101", "214", "401", "704", "1031", "1128", "1224", "1225"}
)


@lru_cache(maxsize=1)
def load_templates() -> dict[str, Any]:
    data = yaml.safe_load(_PATH.read_text(encoding="utf-8")) or {}
    return dict(data.get("templates") or {})


def get_template(name: str) -> dict[str, Any]:
    templates = load_templates()
    if name not in templates:
        raise KeyError(f"Unknown template: {name}")
    return dict(templates[name])


def list_templates() -> list[dict[str, Any]]:
    out = []
    for key, val in load_templates().items():
        row = dict(val)
        row["id"] = key
        out.append(row)
    return out


def apply_template_defaults(
    channel_spec: dict[str, Any], template_id: str
) -> dict[str, Any]:
    """Fill missing break/style fields from a template; never overwrite set values."""
    tmpl = get_template(template_id)
    out = dict(channel_spec)
    out.setdefault("style", tmpl.get("default_style", "prime_2026"))
    out.setdefault("rotation", tmpl.get("rotation", "interleave_wrap"))
    out.setdefault("break_groups", list(tmpl.get("break_groups") or []))
    out.setdefault(
        "station_id_after_each_gap", bool(tmpl.get("station_id_after_each_gap"))
    )
    out.setdefault("long_reel_seconds", int(tmpl.get("long_reel_seconds") or 1200))
    return out
