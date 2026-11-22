"""MCP tool profiles (§7.0)."""

from __future__ import annotations

import os
from typing import Literal

ProfileName = Literal["guided", "planner", "builder", "full"]

GUIDED_TOOLS: list[str] = [
    "channel_guide",
    "channel_list",
    "channel_start",
    "channel_set_requirements",
    "channel_find",
    "channel_job",
    "channel_shortlist",
    "channel_choose",
    "channel_plan",
    "channel_answer",
    "channel_build",
]

# Detail tools (§7.2) — registered when implemented; listed for profile math
DETAIL_TOOLS: list[str] = [
    "builder_set_requirements",
    "builder_discover",
    "builder_inspect_candidates",
    "builder_classify",
    "builder_add_candidates",
    "builder_set_contains",
    "builder_plan",
    "builder_exclude_candidates",
    "builder_set_break_plan",
    "builder_validate",
    "builder_report",
    "discover_youtube",
    "inspect_youtube_video",
    "discover_archive",
    "inspect_archive_item",
]


def resolve_profile(cli: str | None = None) -> ProfileName:
    raw = (cli or os.environ.get("STREAMTV_MCP_PROFILE") or "guided").strip().lower()
    if raw not in ("guided", "planner", "builder", "full"):
        return "guided"
    return raw  # type: ignore[return-value]


def tools_for_profile(profile: ProfileName, legacy_names: list[str]) -> list[str]:
    if profile == "guided":
        names = list(GUIDED_TOOLS)
    elif profile == "planner":
        names = [n for n in GUIDED_TOOLS if n != "channel_build"]
    elif profile == "builder":
        names = list(GUIDED_TOOLS) + list(DETAIL_TOOLS)
    else:
        names = list(GUIDED_TOOLS) + list(DETAIL_TOOLS) + list(legacy_names)

    restrict = os.environ.get("STREAMTV_MCP_TOOLS", "").strip()
    if restrict:
        allow = {x.strip() for x in restrict.split(",") if x.strip()}
        names = [n for n in names if n in allow]
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


ANNOTATIONS: dict[str, dict[str, bool]] = {
    "channel_guide": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_list": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_job": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_shortlist": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_start": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
    "channel_set_requirements": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_choose": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_plan": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_answer": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "channel_find": {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
    "channel_build": {
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
}


def annotations_for(name: str) -> dict[str, bool]:
    if name in ANNOTATIONS:
        return dict(ANNOTATIONS[name])
    if name.startswith(("builder_get", "builder_list", "streamtv_list", "streamtv_get")):
        return {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    if "delete" in name or name in ("builder_build", "streamtv_update_channel"):
        return {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    if name.startswith("discover_") or name.startswith("inspect_"):
        return {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    return {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
