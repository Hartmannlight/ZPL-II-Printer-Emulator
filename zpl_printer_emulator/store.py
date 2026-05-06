from __future__ import annotations

from collections import OrderedDict
from threading import RLock

from .models import JobStatus, PrintJob


class JobStore:
    def __init__(self, *, max_jobs: int = 50) -> None:
        self._max_jobs = max_jobs
        self._jobs: OrderedDict[str, PrintJob] = OrderedDict()
        self._lock = RLock()

    def add(self, zpl: str, *, bytes_received: int) -> PrintJob:
        job = PrintJob(zpl=zpl, bytes_received=bytes_received)
        with self._lock:
            self._jobs[job.id] = job
            self._trim()
        return job

    def mark_rendered(self, job_id: str, image_png: bytes) -> PrintJob:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(update={"status": JobStatus.rendered, "image_png": image_png})
            self._jobs[job_id] = updated
            return updated

    def mark_failed(self, job_id: str, error: str) -> PrintJob:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(update={"status": JobStatus.failed, "error": error})
            self._jobs[job_id] = updated
            return updated

    def get(self, job_id: str) -> PrintJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def latest(self, *, limit: int = 20) -> list[PrintJob]:
        with self._lock:
            jobs = list(reversed(self._jobs.values()))
            return jobs[:limit]

    def _trim(self) -> None:
        while len(self._jobs) > self._max_jobs:
            self._jobs.popitem(last=False)
