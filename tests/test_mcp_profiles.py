"""MCP profiles and annotations (§7.0 / §7.3)."""

from __future__ import annotations

from mcp_streamtv.guided import GUIDED_SPECS
from mcp_streamtv.main import DETAIL_SPECS, LEGACY_TOOL_SPECS, _active_specs
from mcp_streamtv.profiles import (
    GUIDED_TOOLS,
    annotations_for,
    resolve_profile,
    tools_for_profile,
)


def test_guided_has_exactly_11_tools() -> None:
    assert len(GUIDED_TOOLS) == 11
    assert len(GUIDED_SPECS) == 11
    names = tools_for_profile("guided", legacy_names=[n for n, _ in LEGACY_TOOL_SPECS])
    assert names == GUIDED_TOOLS
    assert "channel_build" in names


def test_planner_omits_channel_build() -> None:
    names = tools_for_profile("planner", legacy_names=[])
    assert "channel_build" not in names
    assert len(names) == 10


def test_builder_includes_detail_tools() -> None:
    names = tools_for_profile("builder", legacy_names=[])
    assert "builder_discover" in names
    assert "channel_guide" in names
    assert len(names) == 11 + 15


def test_full_includes_legacy() -> None:
    legacy = [n for n, _ in LEGACY_TOOL_SPECS]
    names = tools_for_profile("full", legacy_names=legacy)
    assert "streamtv_list_channels" in names
    assert "channel_guide" in names
    assert "builder_report" in names


def test_active_specs_guided_default(monkeypatch) -> None:
    monkeypatch.delenv("STREAMTV_MCP_PROFILE", raising=False)
    assert resolve_profile() == "guided"
    specs = _active_specs("guided")
    assert len(specs) == 11
    blob = str(specs)
    assert len(blob) <= 16000


def test_annotations_table_for_guided() -> None:
    for name in GUIDED_TOOLS:
        ann = annotations_for(name)
        assert "readOnlyHint" in ann
        assert "destructiveHint" in ann
        assert "idempotentHint" in ann
        assert "openWorldHint" in ann
    assert annotations_for("channel_build")["destructiveHint"] is True
    assert annotations_for("channel_guide")["readOnlyHint"] is True
    assert annotations_for("channel_find")["openWorldHint"] is True


def test_annotations_for_full_profile_tools() -> None:
    legacy = [n for n, _ in LEGACY_TOOL_SPECS]
    for name in tools_for_profile("full", legacy_names=legacy):
        ann = annotations_for(name)
        assert isinstance(ann["readOnlyHint"], bool)
