"""Load community source manifests from data/builder_sources/*.yaml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml

from streamtv.builder.sources.types import AuthMethod, BuilderSourceSpec, SourceAuthSpec

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
COMMUNITY_DIR = ROOT / "data" / "builder_sources"

_VALID_AUTH: set[str] = {"playwright", "password", "token", "cookies", "none"}


def _parse_auth(raw: object) -> SourceAuthSpec:
    if not isinstance(raw, dict):
        return SourceAuthSpec()
    method = str(raw.get("method", "none"))
    if method not in _VALID_AUTH:
        raise ValueError(f"Invalid auth.method: {method}")
    return SourceAuthSpec(
        method=method,  # type: ignore[arg-type]
        login_url=raw.get("login_url"),
        cookies_domain=raw.get("cookies_domain"),
    )


def parse_manifest(data: dict) -> BuilderSourceSpec:
    source_id = str(data.get("id", "")).strip()
    if not source_id:
        raise ValueError("Community manifest missing id")
    label = str(data.get("label", source_id)).strip()
    hosts = data.get("hosts") or []
    if not isinstance(hosts, list) or not hosts:
        raise ValueError(f"Community manifest {source_id}: hosts required")
    auth_methods: list[AuthMethod] = []
    auth = _parse_auth(data.get("auth", {}))
    if auth.method != "none":
        auth_methods.append(auth.method)
    else:
        auth_methods = ["cookies"]
    url_patterns = data.get("url_patterns") or {}
    placeholder_parts = []
    if isinstance(url_patterns, dict):
        for key, pattern in url_patterns.items():
            placeholder_parts.append(f"https://{hosts[0]}{pattern}")
    url_placeholder = "\n".join(placeholder_parts) if placeholder_parts else f"https://{hosts[0]}/..."
    return BuilderSourceSpec(
        id=f"community:{source_id}",
        label=label,
        status="community",
        hosts=[str(h).lower() for h in hosts],
        auth_methods=auth_methods,
        url_placeholder=url_placeholder,
        supports_expand=bool(data.get("supports_expand", False)),
        playout_ready=bool(data.get("playout_ready", False)),
        resolver_source=str(data.get("channel_source", source_id)),
        docs_anchor="community-sources",
        auth=auth,
        module=data.get("module"),
    )


def load_community_sources(directory: Optional[Path] = None) -> list[BuilderSourceSpec]:
    base = directory or COMMUNITY_DIR
    base.mkdir(parents=True, exist_ok=True)
    specs: list[BuilderSourceSpec] = []
    for path in sorted(base.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Manifest must be a YAML mapping")
            specs.append(parse_manifest(raw))
        except Exception as exc:
            logger.warning("Skipping community source %s: %s", path.name, exc)
    return specs


def url_matches_spec(url: str, spec: BuilderSourceSpec) -> bool:
    if spec.id == "plex":
        return url.lower().startswith("plex://") or "/library/metadata/" in url
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    for pattern in spec.hosts:
        pattern = pattern.lower().lstrip(".")
        if host == pattern or host.endswith(f".{pattern}") or pattern in host:
            return True
    return False
