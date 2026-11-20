"""HTTP tests for /api/backup endpoints."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from streamtv.config import config
from streamtv.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setenv("STREAMTV_BACKUP_DIR", str(backup_dir))
    # Reset scheduler singleton so it picks up env
    import streamtv.backup.scheduler as sched_mod

    sched_mod._scheduler = None
    monkeypatch.setattr(config.backup, "enabled", True)
    monkeypatch.setattr(config.backup, "include_secrets", False)
    monkeypatch.setattr(config.security, "api_key_required", False)
    return TestClient(app)


def test_backup_status(client: TestClient) -> None:
    r = client.get("/api/backup/status")
    assert r.status_code == 200
    data = r.json()
    assert "backup_dir" in data
    assert data["format_version"] == 1
    assert "warning" in data


def test_backup_now_and_download(client: TestClient, tmp_path: Path) -> None:
    r = client.post("/api/backup/now")
    assert r.status_code == 200, r.text
    body = r.json()
    assert Path(body["path"]).is_file()

    r2 = client.get("/api/backup/latest")
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("application/zip")
    assert r2.content[:2] == b"PK"


def test_download_requires_auth_when_enabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post("/api/backup/now")
    monkeypatch.setattr(config.security, "api_key_required", True)
    monkeypatch.setattr(config.security, "access_token", "secret-token")

    r = client.get("/api/backup/latest")
    assert r.status_code == 401

    r2 = client.get(
        "/api/backup/latest",
        headers={"X-API-Key": "secret-token"},
    )
    assert r2.status_code == 200


def test_restore_rejects_garbage(client: TestClient) -> None:
    files = {"file": ("bad.zip", io.BytesIO(b"not-a-zip"), "application/zip")}
    r = client.post("/api/backup/restore", files=files)
    assert r.status_code == 400


def test_restore_dry_run_ok(client: TestClient) -> None:
    # Create a real backup then re-upload it
    client.post("/api/backup/now")
    latest = client.get("/api/backup/latest")
    files = {"file": ("streamtv-backup-latest.zip", io.BytesIO(latest.content), "application/zip")}
    r = client.post("/api/backup/restore?dry_run=true", files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "validated"
    assert data["dry_run"] is True
    assert data["restart_required"] is False
