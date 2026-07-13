"""Stable HDHomeRun DeviceID persistence.

Plex keys tuners as device://tv.plex.grabbers.hdhomerun/<DeviceID>.
A placeholder FFFFFFFF (or any change after discovery) causes silent
dedupe / "already known" confusion. Generate once, persist forever.
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

DEVICE_ID_FILE = Path("data/hdhomerun_device_id")
PLACEHOLDER_IDS = frozenset({"FFFFFFFF", "ffffffff", "00000000", ""})


def ensure_stable_device_id(
    configured: str | None,
    persist_path: Path = DEVICE_ID_FILE,
) -> str:
    """Return an 8-hex DeviceID, generating and persisting if needed."""
    configured = (configured or "").strip()

    if persist_path.exists():
        stored = persist_path.read_text().strip().upper()
        if _is_valid(stored):
            if configured and configured.upper() not in PLACEHOLDER_IDS:
                if configured.upper() != stored:
                    logger.warning(
                        "Ignoring config hdhomerun.device_id=%s — using "
                        "persisted DeviceID %s (never change after Plex discovery)",
                        configured,
                        stored,
                    )
            return stored

    if configured and configured.upper() not in PLACEHOLDER_IDS and _is_valid(configured):
        device_id = configured.upper()
    else:
        device_id = secrets.token_hex(4).upper()
        logger.info(
            "Generated stable HDHomeRun DeviceID %s (was placeholder %r)",
            device_id,
            configured,
        )

    persist_path.parent.mkdir(parents=True, exist_ok=True)
    persist_path.write_text(device_id + "\n")
    try:
        persist_path.chmod(0o644)
    except OSError:
        pass
    logger.info(f"Persisted HDHomeRun DeviceID to {persist_path}")
    return device_id


def _is_valid(value: str) -> bool:
    return len(value) == 8 and all(c in "0123456789ABCDEF" for c in value.upper())
