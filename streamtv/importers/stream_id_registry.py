"""Load-time enforcement of globally unique channel-stream ids.

Duplicate stream ids across channel YAML files cause cache source_id
collisions (wrong ``.part`` cache hits -> Plex "Playback stopped";
LESSONS_LEARNED Issues 18-21). This module makes uniqueness a hard import
invariant instead of relying on the standalone audit script.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Tuple

import yaml

logger = logging.getLogger(__name__)

# Source files that legitimately duplicate ids from real channel files.
_EXCLUDED_NAME_PREFIXES = ("channels_generated_",)
_EXCLUDED_NAMES = {"channels_example.yaml", "manifest.yaml"}


class DuplicateStreamIdError(ValueError):
    """Raised when two streams share an id across the channel data set."""


def _iter_stream_ids(path: Path) -> Iterable[Tuple[str, str]]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        logger.warning(f"Skipping unparseable YAML {path.name}: {exc}")
        return
    for channel in data.get("channels", []) or []:
        number = str(channel.get("number", "?"))
        for stream in channel.get("streams", []) or []:
            stream_id = stream.get("id")
            if stream_id:
                yield str(stream_id), number


def assert_unique_stream_ids(data_dir: Path) -> Dict[str, Tuple[str, str]]:
    """Scan every channel YAML in ``data_dir`` and fail on duplicate ids.

    Returns the id -> (file, channel_number) registry on success.
    """
    registry: Dict[str, Tuple[str, str]] = {}
    duplicates: list[str] = []

    for path in sorted(data_dir.glob("*.yaml")):
        if path.name in _EXCLUDED_NAMES or path.name.startswith(
            _EXCLUDED_NAME_PREFIXES
        ):
            continue
        for stream_id, channel_number in _iter_stream_ids(path):
            existing = registry.get(stream_id)
            if existing and existing != (path.name, channel_number):
                duplicates.append(
                    f"id '{stream_id}' in {path.name} (ch {channel_number}) "
                    f"already used by {existing[0]} (ch {existing[1]})"
                )
            else:
                registry[stream_id] = (path.name, channel_number)

    if duplicates:
        raise DuplicateStreamIdError(
            "Duplicate stream ids detected — run "
            "scripts/ensure_unique_yaml_stream_ids.py then "
            "scripts/sync_media_source_ids_from_yaml.py:\n  "
            + "\n  ".join(duplicates)
        )
    return registry
