"""Media API PATCH/create tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from streamtv.main import app
from streamtv.streaming.stream_manager import StreamSource


def test_patch_media_not_found() -> None:
    client = TestClient(app)
    resp = client.patch("/api/media/999999999", json={"title": "After"})
    assert resp.status_code == 404


def test_create_media_from_url_mock() -> None:
    client = TestClient(app)
    mock_info = {
        "title": "PBS Test",
        "duration": 3600,
        "description": "desc",
    }
    with patch(
        "streamtv.api.media.stream_manager.get_media_info",
        new_callable=AsyncMock,
        return_value=mock_info,
    ):
        with patch(
            "streamtv.api.media.stream_manager.detect_source",
            return_value=StreamSource.PBS,
        ):
            resp = client.post(
                "/api/media",
                json={"url": "https://www.pbs.org/show/nature/"},
            )
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert body.get("source") == "pbs" or "pbs" in str(body.get("url", "")).lower()
