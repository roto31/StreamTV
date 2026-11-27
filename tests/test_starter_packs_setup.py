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


def test_starter_pack_files_exist() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "starter_packs"
    for number in ("9101", "9102", "9103", "9104"):
        assert (root / f"channel_{number}.yaml").is_file()
        assert (root / "schedules" / f"{number}.yml").is_file()
        assert (root / "icons" / f"channel_{number}.png").is_file()


def test_install_runtime_failure_message_is_short() -> None:
    from streamtv.setup.runtime_install import summarize_failure

    steps = {"com_streamtv": {"ok": False, "detail": "missing /x/scripts/install-com-streamtv-launchagent.sh"}}
    message = summarize_failure(steps)
    assert "installer script is missing" in message
    assert "{" not in message and "/x/" not in message


def test_starter_packs_root_finds_bundle_or_cwd(tmp_path: Path, monkeypatch) -> None:
    from streamtv.setup import starter_packs as sp

    # Empty cwd should still resolve to the repo pack tree shipped with the package.
    monkeypatch.chdir(tmp_path)
    root = sp.starter_packs_root()
    assert sp._pack_complete(root)


def test_ensure_starter_packs_seeds_workdir(tmp_path: Path, monkeypatch) -> None:
    from streamtv.setup import starter_packs as sp

    monkeypatch.chdir(tmp_path)
    seeded = sp.ensure_starter_packs_in_workdir(tmp_path)
    assert seeded is not None
    assert sp._pack_complete(tmp_path / "data" / "starter_packs")
    body = sp.list_catalog()
    assert all(c["available"] is True for c in body)


def test_sanitize_stream_type_and_year_aliases() -> None:
    from streamtv.setup.starter_packs import sanitize_stream_dict

    music = sanitize_stream_dict(
        {"id": "a", "type": "music_video", "year": "1984", "title": "Jump"}
    )
    assert music["type"] == "episode"
    assert music["year"] == 1984

    trailer = sanitize_stream_dict(
        {"id": "b", "type": "trailer", "year": "circa 1990", "title": "Preview"}
    )
    assert trailer["type"] == "commercial"
    assert trailer["year"] == 1990

    bad_year = sanitize_stream_dict({"id": "c", "type": "movie", "year": "unknown"})
    assert "year" not in bad_year


def test_sample_channels_install_returns_400_on_errors(monkeypatch) -> None:
    from streamtv.api import setup as setup_api
    from streamtv.main import app
    from streamtv.setup.starter_packs import StarterInstallResult

    async def _fake_install(numbers, *, workdir=None, db_session=None):
        return StarterInstallResult(
            ok=False,
            installed=["9103"],
            detail="installed=['9103']; errors=['9101: validation failed']",
            errors=["9101: validation failed"],
        )

    monkeypatch.setattr(setup_api, "install_starter_channels", _fake_install)
    client = TestClient(app)
    r = client.post("/api/setup/sample-channels", json={"channels": ["9101", "9103"]})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["ok"] is False
    assert "9101: validation failed" in detail["errors"]
    assert detail["installed"] == ["9103"]
