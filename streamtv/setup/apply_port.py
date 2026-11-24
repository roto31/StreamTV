"""Write server.port + base_url into the active config file."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

import yaml

logger = logging.getLogger(__name__)


def _config_path() -> Path:
    return Path(os.environ.get("STREAMTV_CONFIG", "config.yaml")).expanduser()


def _example_config() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "config.example.yaml"


def ensure_config_exists() -> Path:
    path = _config_path()
    if path.is_file():
        return path
    example = _example_config()
    if example.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example, path)
        logger.info("Seeded config from example → %s", path)
        return path
    raise FileNotFoundError(f"No config at {path} and no config.example.yaml")


def _rewrite_base_url(existing: str, port: int) -> str:
    raw = (existing or f"http://127.0.0.1:{port}").strip() or f"http://127.0.0.1:{port}"
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    scheme = parsed.scheme or "http"
    netloc = f"{host}:{port}"
    return urlunparse((scheme, netloc, parsed.path or "", "", "", ""))


def apply_port(port: int) -> Dict[str, Any]:
    """Persist port + base_url; update in-memory config if loaded."""
    if not (1 <= int(port) <= 65535):
        raise ValueError(f"Invalid port: {port}")

    path = ensure_config_exists()
    data: Dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = loaded
    except OSError as exc:
        raise RuntimeError(f"Cannot read {path}: {exc}") from exc

    server = dict(data.get("server") or {})
    server["port"] = int(port)
    server["base_url"] = _rewrite_base_url(str(server.get("base_url") or ""), int(port))
    data["server"] = server

    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    try:
        from ..config import config

        config.update_section(
            "server",
            {"port": int(port), "base_url": server["base_url"]},
        )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("In-memory config update failed (file written): %s", exc)

    return {
        "port": int(port),
        "base_url": server["base_url"],
        "config_path": str(path.resolve()),
        "restart_required": True,
    }
