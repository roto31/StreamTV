"""In-process async job tracking for Channel Builder."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Coroutine, Optional

from .models import BuilderJob

ROOT = Path(__file__).resolve().parents[2]
JOBS_DIR = ROOT / "data" / "builder_jobs"


class JobStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or JOBS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, asyncio.Task] = {}

    def _path(self, job_id: str) -> Path:
        return self.base_dir / f"{job_id}.json"

    def get(self, job_id: str) -> Optional[BuilderJob]:
        path = self._path(job_id)
        if not path.exists():
            return None
        return BuilderJob.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, job: BuilderJob) -> BuilderJob:
        job.updated_at = datetime.now(timezone.utc).isoformat()
        self._path(job.id).write_text(job.model_dump_json(indent=2), encoding="utf-8")
        return job

    def start_background(
        self,
        job: BuilderJob,
        coro_factory: Callable[[BuilderJob], Coroutine],
    ) -> BuilderJob:
        self.save(job)

        async def _run() -> None:
            current = self.get(job.id) or job
            current.status = "running"
            self.save(current)
            try:
                await coro_factory(current)
                current = self.get(job.id) or current
                if current.status == "running":
                    current.status = "completed"
                self.save(current)
            except Exception as exc:
                current = self.get(job.id) or current
                current.status = "failed"
                current.errors.append(str(exc))
                self.save(current)

        task = asyncio.create_task(_run())
        self._tasks[job.id] = task
        return job


job_store = JobStore()
