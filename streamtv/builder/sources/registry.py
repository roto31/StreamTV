"""Built-in and community source registry for Channel Builder."""

from __future__ import annotations

from typing import Optional

from streamtv.builder.sources.builtins import BUILTIN_SPECS
from streamtv.builder.sources.community_loader import load_community_sources, url_matches_spec
from streamtv.builder.sources.types import BuilderSourceSpec

_registry: dict[str, BuilderSourceSpec] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    reload_sources()


def reload_sources() -> list[BuilderSourceSpec]:
    global _registry, _loaded
    _registry = {spec.id: spec for spec in BUILTIN_SPECS}
    for spec in load_community_sources():
        _registry[spec.id] = spec
    _loaded = True
    return list_sources()


def list_sources() -> list[BuilderSourceSpec]:
    _ensure_loaded()
    return list(_registry.values())


def get_source(source_id: str) -> Optional[BuilderSourceSpec]:
    _ensure_loaded()
    return _registry.get(source_id)


def require_source(source_id: str) -> BuilderSourceSpec:
    spec = get_source(source_id)
    if not spec:
        raise ValueError(f"Unknown source: {source_id}")
    return spec


def detect_source_for_url(url: str) -> Optional[BuilderSourceSpec]:
    _ensure_loaded()
    for spec in _registry.values():
        if spec.status == "coming_soon":
            continue
        if url_matches_spec(url, spec):
            return spec
    return None


def source_for_kind(kind: str) -> Optional[BuilderSourceSpec]:
    mapping = {
        "archive": "archive_org",
        "archive_collection": "archive_org",
        "youtube": "youtube",
        "youtube_playlist": "youtube",
        "pbs": "pbs",
        "pbs_show": "pbs",
        "plex": "plex",
    }
    source_id = mapping.get(kind)
    return get_source(source_id) if source_id else None
