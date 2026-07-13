"""Tests for Tunarr integration API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from streamtv.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_tunarr_status_not_configured(client: TestClient) -> None:
    with patch("streamtv.api.integrations_tunarr.get_tunarr_base_url", return_value=None):
        resp = client.get("/api/integrations/tunarr/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["reachable"] is False


def test_tunarr_status_reachable(client: TestClient) -> None:
    mock_health = AsyncMock(return_value={"reachable": True, "health": {"status": "ok"}})
    with patch("streamtv.api.integrations_tunarr.get_tunarr_base_url", return_value="http://127.0.0.1:8000"):
        with patch("streamtv.integrations.tunarr_client.TunarrClient.health", mock_health):
            resp = client.get("/api/integrations/tunarr/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["reachable"] is True
    assert body["web_url"] == "http://127.0.0.1:8000/web"


def test_tunarr_media_sources_503_when_unconfigured(client: TestClient) -> None:
    with patch("streamtv.api.integrations_tunarr.get_tunarr_base_url", return_value=None):
        resp = client.get("/api/integrations/tunarr/media-sources")
    assert resp.status_code == 503
