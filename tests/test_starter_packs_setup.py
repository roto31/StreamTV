"""Tests for universal first-run starter packs + runtime install helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_sample_channels_catalog() -> None:
    from streamtv.main import app

    client = TestClient(app)
    r = client.get("/api/setup/sample-channels")
    assert r.status_code == 200
    body = r.json()
    assert "channels" in body
    numbers = {c["number"] for c in body["channels"]}
    assert {"9101", "9102", "9103", "9104"} <= numbers


def test_setup_status_includes_sample_channels(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STREAMTV_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from streamtv.main import app

    client = TestClient(app)
    r = client.get("/api/setup/status")
    assert r.status_code == 200
    assert "sample_channels" in r.json()
    assert "install_modes" in r.json()


def test_validate_workdir_missing(tmp_path: Path) -> None:
    from streamtv.setup.runtime_install import validate_workdir

    missing = tmp_path / "nope"
    result = validate_workdir(missing, mode="repo")
    assert result.ok is False


def test_tuner_manager_default_has_no_lab_ip() -> None:
    from streamtv.config import TunerEndpointConfig

    assert "192.168.1." not in (TunerEndpointConfig().url or "")


def test_starter_pack_files_exist() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "starter_packs"
    for number in ("9101", "9102", "9103", "9104"):
        assert (root / f"channel_{number}.yaml").is_file()
        assert (root / "schedules" / f"{number}.yml").is_file()
        assert (root / "icons" / f"channel_{number}.png").is_file()
