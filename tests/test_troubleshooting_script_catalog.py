"""Public troubleshooting script catalog — list shape and safety."""

from __future__ import annotations

from streamtv.troubleshooting.script_catalog import (
    TROUBLESHOOTING_SCRIPTS,
    list_scripts_public,
)


def test_catalog_has_playback_and_diagnostics() -> None:
    cats = {m.get("category") for m in TROUBLESHOOTING_SCRIPTS.values()}
    assert "playback" in cats
    assert "diagnostics" in cats


def test_list_scripts_public_includes_hover_and_id() -> None:
    pub = list_scripts_public()
    assert "prewarm_youtube_cache" in pub
    entry = pub["prewarm_youtube_cache"]
    assert entry["id"] == "prewarm_youtube_cache"
    assert entry["hover"]
    assert entry["runnable"] is True
    assert "192.168." not in entry["hover"]
    assert "/Users/" not in entry["hover"]


def test_kickstart_not_runnable_from_api() -> None:
    meta = TROUBLESHOOTING_SCRIPTS["kickstart_with_prewarm"]
    assert meta.get("runnable") is False


def test_no_private_lan_in_catalog_copy() -> None:
    blob = str(TROUBLESHOOTING_SCRIPTS)
    assert "192.168." not in blob
    assert "10.0." not in blob
    assert "/Users/roto" not in blob
