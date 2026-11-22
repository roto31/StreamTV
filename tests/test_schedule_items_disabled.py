"""Schedule-item mutations return 410 (YAML authority)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from streamtv.main import app


def test_schedule_item_mutations_return_410() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/schedule-items",
        json={
            "schedule_id": 1,
            "collection_type": "collection",
            "collection_id": 1,
            "index": 0,
        },
    )
    assert create.status_code == 410

    update = client.put("/api/schedule-items/1", json={"index": 1})
    assert update.status_code == 410

    delete = client.delete("/api/schedule-items/1")
    assert delete.status_code == 410

    move = client.post("/api/schedule-items/1/move?direction=up")
    assert move.status_code == 410
