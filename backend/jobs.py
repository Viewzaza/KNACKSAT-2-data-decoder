"""Tiny in-memory async job tracker for decode requests.

A single process is fine here: this app is a personal/small-station tool, not
a multi-tenant service, and gr_satellites is CPU-bound so we cap concurrency
via the semaphore below rather than reaching for a task queue.
"""
import asyncio
import itertools
import time
from typing import Any

_jobs: dict[int, dict[str, Any]] = {}
_id_counter = itertools.count(1)
_semaphore = asyncio.Semaphore(2)


def create_job(observation_id: int) -> int:
    job_id = next(_id_counter)
    _jobs[job_id] = {
        "id": job_id,
        "observation_id": observation_id,
        "status": "queued",
        "created": time.time(),
        "result": None,
        "error": None,
    }
    return job_id


def get_job(job_id: int) -> dict | None:
    return _jobs.get(job_id)


async def run_job(job_id: int, coro_factory):
    job = _jobs[job_id]
    async with _semaphore:
        job["status"] = "running"
        try:
            job["result"] = await coro_factory()
            job["status"] = "done"
        except Exception as exc:  # noqa: BLE001 - surface any decode failure to the UI
            job["error"] = str(exc)
            job["status"] = "error"
