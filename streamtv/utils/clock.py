"""Naive-UTC wall clock (replacement for the deprecated ``datetime.utcnow()``)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Return the current UTC time without tzinfo.

    Stored timestamps and playout/EPG math compare naive UTC values, so the
    result must stay tz-naive to remain comparable with existing rows.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
