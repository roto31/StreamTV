"""Cache directory readiness + deferred start when TunarrRAM is missing.

Used by ``streamtv.main`` lifespan — not part of streaming bedrock
(``streamtv/cache/**``); only orchestrates when CacheManager may start.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def cache_volume_status(cache_directory: str) -> Tuple[bool, str]:
    """Return (ready, reason). Ready means parent mount exists and is writable."""
    path = Path(cache_directory).expanduser()
    # Prefer the volume root for /Volumes/TunarrRAM/...
    parts = path.parts
    if len(parts) >= 3 and parts[1] == "Volumes":
        volume = Path("/") / parts[1] / parts[2]
        if not volume.exists():
            return False, f"volume not mounted: {volume}"
        if not os.access(volume, os.W_OK):
            return False, f"volume not writable (Errno 13?): {volume}"
    parent = path.parent
    if not parent.exists():
        return False, f"parent missing: {parent}"
    if not os.access(parent, os.W_OK):
        return False, f"parent not writable: {parent}"
    return True, "ok"


def ensure_cache_dir(cache_directory: str) -> Path:
    """Create cache dir when volume is ready; raises OSError loudly otherwise."""
    ready, reason = cache_volume_status(cache_directory)
    if not ready:
        raise OSError(f"Cache directory not ready: {reason} ({cache_directory})")
    path = Path(cache_directory).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path
