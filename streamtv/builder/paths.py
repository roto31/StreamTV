"""Repo / data root for Channel Builder (throwaway e2e via STREAMTV_REPO_ROOT)."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Canonical StreamTV checkout, or isolated tree for e2e.

    ``STREAMTV_REPO_ROOT`` (or ``STREAMTV_HOME``) redirects data/schedules writes
    without touching production. Package imports still load from the real install.
    """
    for key in ("STREAMTV_REPO_ROOT", "STREAMTV_HOME"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return repo_root() / "data"


def schedules_dir() -> Path:
    return repo_root() / "schedules"
