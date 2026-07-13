"""Tuner manager — proxy upstream HDHomeRun emulators (e.g. Tunarr) for Plex GUI add."""

from .device_ids import ensure_tuner_device_id
from .guide_merge import merge_xmltv
from .proxy import TunerProxy

__all__ = ["TunerProxy", "ensure_tuner_device_id", "merge_xmltv"]
