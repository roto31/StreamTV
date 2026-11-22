"""Archive.org and YouTube discovery for Channel Creator."""

from .archive import build_archive_queries, inspect_archive_item, search_archive
from .audience import (
    AUDIENCE_CHOICES_PLAIN,
    AUDIENCE_QUESTION,
    apply_audience_to_requirements,
    normalize_audience,
)
from .youtube import inspect_youtube_video, search_youtube

__all__ = [
    "AUDIENCE_CHOICES_PLAIN",
    "AUDIENCE_QUESTION",
    "apply_audience_to_requirements",
    "build_archive_queries",
    "inspect_archive_item",
    "normalize_audience",
    "search_archive",
    "inspect_youtube_video",
    "search_youtube",
]
