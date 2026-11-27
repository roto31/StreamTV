"""utc_now_naive keeps the naive-UTC contract used by DB rows and playout math."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from streamtv.utils.clock import utc_now_naive

CLOCK_TOLERANCE = timedelta(seconds=5)


def test_utc_now_naive_is_naive_utc() -> None:
    now = utc_now_naive()
    reference = datetime.now(timezone.utc).replace(tzinfo=None)

    assert now.tzinfo is None
    assert abs(reference - now) < CLOCK_TOLERANCE
