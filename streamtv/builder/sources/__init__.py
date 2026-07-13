"""Public API for Channel Builder source registry."""

from streamtv.builder.sources.community_loader import url_matches_spec
from streamtv.builder.sources.registry import (
    detect_source_for_url,
    get_source,
    list_sources,
    reload_sources,
    require_source,
    source_for_kind,
)
from streamtv.builder.sources.types import BuilderSourceSpec

__all__ = [
    "BuilderSourceSpec",
    "detect_source_for_url",
    "get_source",
    "list_sources",
    "reload_sources",
    "require_source",
    "source_for_kind",
    "url_matches_spec",
]
