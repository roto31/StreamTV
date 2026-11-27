"""trigger_now must run the job now, not offset by the scheduler's UTC offset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("apscheduler")
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: E402

from streamtv.cache.download_scheduler import DownloadScheduler  # noqa: E402

SCHEDULER_TZ = ZoneInfo("America/Chicago")
JOB_ID = "test-job"
MAX_DRIFT = timedelta(seconds=5)


def _noop() -> None:
    return None


async def test_trigger_now_schedules_job_at_current_utc_instant() -> None:
    scheduler = AsyncIOScheduler(timezone=SCHEDULER_TZ)
    scheduler.add_job(
        _noop, "date", run_date=datetime.now(timezone.utc) + timedelta(days=1), id=JOB_ID
    )
    scheduler.start(paused=True)
    try:
        download_scheduler = DownloadScheduler.__new__(DownloadScheduler)
        download_scheduler._scheduler = scheduler

        assert await download_scheduler.trigger_now(JOB_ID) is True

        next_run = scheduler.get_job(JOB_ID).next_run_time
        assert abs(next_run - datetime.now(timezone.utc)) < MAX_DRIFT
    finally:
        scheduler.shutdown(wait=False)


async def test_trigger_now_unknown_job_returns_false() -> None:
    scheduler = AsyncIOScheduler(timezone=SCHEDULER_TZ)
    scheduler.start(paused=True)
    try:
        download_scheduler = DownloadScheduler.__new__(DownloadScheduler)
        download_scheduler._scheduler = scheduler

        assert await download_scheduler.trigger_now("missing") is False
    finally:
        scheduler.shutdown(wait=False)
