"""Import API tests."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from streamtv.main import app


def test_yaml_path_import_forbidden_by_default() -> None:
    client = TestClient(app)
    with patch("streamtv.config.config.security.allow_local_path_import", False):
        resp = client.post(
            "/api/import/channels/yaml/path",
            params={"file_path": "/tmp/test.yaml"},
        )
    assert resp.status_code == 403
