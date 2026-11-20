"""Backup manifest (format_version 1)."""

from __future__ import annotations

import hashlib
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def app_version() -> str:
    try:
        version_file = Path(__file__).resolve().parents[2] / "VERSION"
        if version_file.is_file():
            return version_file.read_text().strip()
    except OSError:
        pass
    return "unknown"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    *,
    format_version: int,
    members: List[Dict[str, Any]],
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "format_version": format_version,
        "app_version": app_version(),
        "created_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "hostname": socket.gethostname(),
        "members": members,
        "notes": notes or [],
    }


def write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def read_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
