"""HDHomeRun route smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from streamtv.main import app


def test_discover_json() -> None:
    client = TestClient(app)
    resp = client.get("/hdhomerun/discover.json")
    assert resp.status_code == 200
    body = resp.json()
    assert "FriendlyName" in body or "DeviceID" in body


def test_lineup_json() -> None:
    client = TestClient(app)
    resp = client.get("/hdhomerun/lineup.json")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_tune_unknown_channel_404() -> None:
    client = TestClient(app)
    resp = client.get("/hdhomerun/auto/v99999999")
    assert resp.status_code in (404, 503)
