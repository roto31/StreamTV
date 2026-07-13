"""Resolve Tunarr base URL from StreamTV tuner_manager config."""

from __future__ import annotations

from typing import Any, Optional

from ..config import config


def list_tunarr_tuners() -> list[dict[str, Any]]:
    """Return configured tuner entries with name and upstream URL."""
    out: list[dict[str, Any]] = []
    for entry in config.tuner_manager.tuners or []:
        if isinstance(entry, dict):
            name = entry.get("name")
            url = entry.get("url")
        else:
            name = getattr(entry, "name", None)
            url = getattr(entry, "url", None)
        if name and url:
            out.append({"name": str(name), "url": str(url).rstrip("/")})
    return out


def get_tunarr_base_url(preferred_name: str = "tunarr") -> Optional[str]:
    """First matching tuner URL, preferring ``preferred_name``."""
    tuners = list_tunarr_tuners()
    if not tuners:
        return None
    for t in tuners:
        if t["name"] == preferred_name:
            return t["url"]
    return tuners[0]["url"]
