"""Phase 1 red regression for upload import temp-dir isolation (D8)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from streamtv.main import app


def _channel_yaml(number: str, stream_id: str, title: str) -> bytes:
    payload = {
        "channels": [
            {
                "number": number,
                "name": f"Channel {number}",
                "group": "Test",
                "enabled": True,
                "playout_mode": "continuous",
                "streams": [
                    {
                        "id": stream_id,
                        "collection": f"Channel {number}",
                        "type": "event",
                        "source": "youtube",
                        "url": f"https://www.youtube.com/watch?v={stream_id[-11:]}",
                        "title": title,
                        "runtime": "PT3M33S",
                    }
                ],
            }
        ]
    }
    return yaml.safe_dump(payload).encode("utf-8")


def test_d8_upload_import_ignores_stray_yaml_in_system_temp() -> None:
    """D8: a conflicting *.yaml in the OS temp folder must not fail the upload import.

    Current bug: NamedTemporaryFile lands in tempfile.gettempdir(), and
    assert_unique_stream_ids(yaml_path.parent) scans that whole folder.
    """
    shared_id = "d8_collide_shared_stream_id"
    conflict_path = Path(tempfile.gettempdir()) / "d8_stray_conflict_channels.yaml"
    conflict_path.write_bytes(
        _channel_yaml("9088", shared_id, "Stray temp conflict")
    )
    try:
        client = TestClient(app)
        upload = _channel_yaml("9099", shared_id, "Upload under test")
        resp = client.post(
            "/api/import/channels/yaml",
            files={"yaml_file": ("upload_d8.yaml", upload, "application/x-yaml")},
            params={"validate": "true"},
        )
        assert resp.status_code == 200, (
            "D8: upload import failed because assert_unique_stream_ids scanned "
            f"system temp ({tempfile.gettempdir()}), colliding with {conflict_path.name}: "
            f"status={resp.status_code} body={resp.text[:500]}"
        )
    finally:
        if conflict_path.exists():
            conflict_path.unlink()
