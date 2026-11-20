"""Shared pytest fixtures for clean-CI HTTP tests.

GitHub-hosted runners have no operator ``config.yaml`` / ``streamtv.db``.
Disable API-key middleware for mutating requests and ensure SQLite tables exist
(``TestClient`` without a context manager does not run app lifespan / ``init_db``).
"""

from __future__ import annotations

import pytest

from streamtv.config import config
from streamtv.database import init_db


@pytest.fixture(autouse=True)
def _clean_ci_http_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.security, "api_key_required", False)
    monkeypatch.setattr(config.security, "access_token", None)
    init_db()
