"""EPG sync class (A/B/C) resolution for playout-authoritative guide behavior."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from streamtv.database.models import Channel

# Plan defaults — overridden by channel.epg_sync_class or config.playout.epg_sync_class_fallback
_CLASS_A = frozenset({"1986", "1987", "1988", "1991", "1994"})
_CLASS_B = frozenset(
    {
        "80",
        "123",
        "143",
        "1970",
        "1980",
        "1980.1",
        "1984",
        "1984.1",
        "1992",
        "1998",
        "2000",
        "2010",
    }
)
_CLASS_C = frozenset({"11", "1929", "1954", "1982", "1985", "1990"})


def _normalize_class(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    letter = str(value).strip().upper()
    if letter in ("A", "B", "C"):
        return letter
    return None


def resolve_epg_sync_class(
    channel_number: str,
    channel: Optional["Channel"] = None,
) -> str:
    """Return sync class A (short-form), B (archive marathon), or C (cycle/idle)."""
    from streamtv.config import config

    num = str(channel_number).strip()
    if channel is not None:
        db_class = _normalize_class(getattr(channel, "epg_sync_class", None))
        if db_class:
            return db_class

    fallback = getattr(config.playout, "epg_sync_class_fallback", None) or {}
    if isinstance(fallback, dict) and num in fallback:
        mapped = _normalize_class(fallback.get(num))
        if mapped:
            return mapped

    if num in _CLASS_A:
        return "A"
    if num in _CLASS_B:
        return "B"
    if num in _CLASS_C:
        return "C"
    return "C"


def class_playout_settings(sync_class: str) -> dict:
    """Per-class playout/EPG knobs from config."""
    from streamtv.config import config

    classes = getattr(config.playout, "epg_sync_classes", None) or {}
    if not isinstance(classes, dict):
        return {}
    entry = classes.get(sync_class) or classes.get(sync_class.upper()) or {}
    return entry if isinstance(entry, dict) else {}


def playout_authoritative_epg(channel_number: str, channel: Optional["Channel"] = None) -> bool:
    """True when row-0 EPG should always follow live playout (class A default)."""
    sync_class = resolve_epg_sync_class(channel_number, channel)
    settings = class_playout_settings(sync_class)
    if "playout_authoritative_epg" in settings:
        return bool(settings["playout_authoritative_epg"])
    return sync_class == "A"
