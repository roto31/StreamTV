"""Builder HTTP integration smoke tests."""

from __future__ import annotations

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
    assert "youtube" in ids
    assert "archive_org" in ids
    assert "pbs" in ids
