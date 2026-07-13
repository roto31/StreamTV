"""IPTV route smoke tests (read-only)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from streamtv.main import app


def test_channels_m3u() -> None:
    client = TestClient(app)
    resp = client.get("/iptv/channels.m3u")
    assert resp.status_code == 200
    assert "#EXTM3U" in resp.text or resp.text.strip() == ""


def test_xmltv_xml() -> None:
    client = TestClient(app)
    resp = client.get("/iptv/xmltv.xml")
    assert resp.status_code == 200
    assert resp.text.startswith("<?xml") or "<tv" in resp.text
