"""Inert tuner_manager stub ignores legacy YAML enable flags."""

from __future__ import annotations

from pathlib import Path

from streamtv.config import Config


def test_tuner_manager_yaml_enabled_still_inert(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "tuner_manager:\n  enabled: true\n  merged_guide: true\n",
        encoding="utf-8",
    )
    loaded = Config(cfg)
    assert loaded.tuner_manager.enabled is False
    assert loaded.tuner_manager.merged_guide is False
