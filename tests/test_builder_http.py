"""Builder HTTP integration smoke tests."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from streamtv.main import app


def test_builder_draft_create_and_list() -> None:
    client = TestClient(app)
    create = client.post("/api/builder/drafts", json={})
    assert create.status_code == 200
    draft = create.json()
    assert "id" in draft

    listed = client.get("/api/builder/drafts")
    assert listed.status_code == 200
    ids = [d["id"] for d in listed.json()]
    assert draft["id"] in ids


def test_builder_sources_list() -> None:
    client = TestClient(app)
    resp = client.get("/api/builder/sources")
    assert resp.status_code == 200
    sources = resp.json()
    ids = {s["id"] for s in sources}
    assert ids == {"youtube", "archive_org"}
    # Parked first-party sources must not reappear on the live Builder list.
    assert "pbs" not in ids
    assert "plex" not in ids
    assert "vimeo" not in ids


def test_builder_auth_status_includes_metadata_scopes() -> None:
    client = TestClient(app)
    resp = client.get("/api/builder/auth/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "tvdb" in body
    assert "tvmaze" in body
    assert "configured" in body["tvdb"]
    assert "configured" in body["tvmaze"]


def test_builder_auth_tvdb_ok() -> None:
    client = TestClient(app)
    with patch(
        "streamtv.api.builder.apply_tvdb_api_key",
        return_value={"status": "success", "scope": "tvdb"},
    ) as mock_apply:
        resp = client.post("/api/builder/auth/tvdb", json={"api_key": "test-tvdb-key"})
    assert resp.status_code == 200
    assert resp.json()["scope"] == "tvdb"
    mock_apply.assert_called_once_with("test-tvdb-key")


def test_builder_auth_tvdb_empty_key() -> None:
    client = TestClient(app)
    with patch(
        "streamtv.api.builder.apply_tvdb_api_key",
        side_effect=ValueError("TVDB API key is required"),
    ):
        resp = client.post("/api/builder/auth/tvdb", json={"api_key": "  "})
    assert resp.status_code == 400


def test_builder_auth_tvmaze_ok() -> None:
    client = TestClient(app)
    with patch(
        "streamtv.api.builder.apply_tvmaze_credentials",
        return_value={"status": "success", "scope": "tvmaze"},
    ) as mock_apply:
        resp = client.post(
            "/api/builder/auth/tvmaze",
            json={"username": "maze_user", "api_key": "maze_key"},
        )
    assert resp.status_code == 200
    assert resp.json()["scope"] == "tvmaze"
    mock_apply.assert_called_once_with("maze_user", "maze_key")


def test_builder_auth_tvmaze_validation_error() -> None:
    client = TestClient(app)
    with patch(
        "streamtv.api.builder.apply_tvmaze_credentials",
        side_effect=ValueError("TVMaze username is required"),
    ):
        resp = client.post(
            "/api/builder/auth/tvmaze",
            json={"username": "", "api_key": "k"},
        )
    assert resp.status_code == 400
