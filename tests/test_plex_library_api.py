"""Tests for native Plex library API fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from streamtv.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_plex_libraries_requires_config(client: TestClient) -> None:
    with patch("streamtv.api.plex_library.config") as mock_config:
        mock_config.plex.enabled = False
        mock_config.plex.base_url = ""
        mock_config.plex.token = None
        resp = client.get("/api/plex/libraries")
    assert resp.status_code == 400


def test_plex_libraries_mock(client: TestClient) -> None:
    payload = {
        "MediaContainer": {
            "Directory": [
                {"ratingKey": "1", "title": "Movies", "type": "movie"},
                {"ratingKey": "2", "title": "TV", "type": "show"},
            ]
        }
    }
    with patch("streamtv.api.plex_library.config") as mock_config:
        mock_config.plex.enabled = True
        mock_config.plex.base_url = "http://plex.test:32400"
        mock_config.plex.token = "token"
        with patch(
            "streamtv.api.plex_library._plex_get_json",
            AsyncMock(return_value=payload),
        ):
            resp = client.get("/api/plex/libraries")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Movies"
