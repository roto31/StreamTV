"""Per-tuner DeviceID persistence under data/tuner_device_ids/."""

from __future__ import annotations

from pathlib import Path

from ..hdhomerun.device_id import ensure_stable_device_id

TUNER_DEVICE_ID_DIR = Path("data/tuner_device_ids")


def ensure_tuner_device_id(name: str, configured: str | None = None) -> str:
    """Return a stable 8-hex DeviceID for the named tuner proxy."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "tuner"))
    path = TUNER_DEVICE_ID_DIR / safe
    return ensure_stable_device_id(configured, persist_path=path)
