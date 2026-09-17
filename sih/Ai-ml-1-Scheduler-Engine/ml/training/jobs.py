"""Async training-job registry backing ``/internal/train`` (Ai-ml-1 Level 5).

``/internal/train`` returns a ``job_id`` immediately and the Backend polls
``/internal/train/{job_id}/status`` for ``{status, progress}``. Jobs run on a bounded thread pool
so a training request cannot block the decision path, which has a 50 ms budget (NFR-002).

In-process and in-memory by design: the PRD puts Redis-backed queuing in the Backend (Section
15.1), not here. This service just needs to not block.
"""

from __future__ import annotations

import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from ml.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class Job:
    job_id: str
    status: str = "running"          # running | done | failed
    progress: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobRegistry:
    """Tracks background training jobs."""

    def __init__(self, max_workers: int = 2, max_jobs: int = 200) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="train")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self.max_jobs = max_jobs

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> str:
        """Run ``fn(*args, progress=..., **kwargs)`` in the background."""
        job_id = f"job_{uuid4().hex[:8]}"
        job = Job(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = job
            self._evict()

        def progress(fraction: float, detail: dict | None = None) -> None:
            job.progress = float(min(1.0, max(0.0, fraction)))
            if detail:
                job.detail.update(detail)

        def run() -> None:
            try:
                job.result = fn(*args, progress=progress, **kwargs)
                job.progress = 1.0
                job.status = "done"
            except BaseException as exc:  # surface the failure rather than losing the thread
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                job.detail["traceback"] = traceback.format_exc(limit=6)
                log.warning("training job failed", extra={"job_id": job_id, "error": job.error})

        self._pool.submit(run)
        return job_id

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _evict(self) -> None:
        if len(self._jobs) <= self.max_jobs:
            return
        finished = sorted(
            (j for j in self._jobs.values() if j.status != "running"),
            key=lambda j: j.created_at,
        )
        for job in finished[: len(self._jobs) - self.max_jobs]:
            self._jobs.pop(job.job_id, None)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
