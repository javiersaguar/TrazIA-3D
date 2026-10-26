"""Arranque: uv run --extra api arq trazia.queue.worker.WorkerSettings."""

import os
from pathlib import Path

from arq import Retry
from arq.connections import RedisSettings

from trazia.api.jobs import run_job
from trazia.store import Store


async def startup(context):
    context["store"] = Store(
        Path(os.getenv("TRAZIA_DATA", "data")), os.getenv("TRAZIA_DATABASE_URL")
    )


async def shutdown(context):
    context["store"].close()


async def execute_job(context, job_id: str):
    delay = await run_job(context["store"], job_id)
    if delay is not None:
        raise Retry(defer=delay + 1)


class WorkerSettings:
    functions = [execute_job]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("TRAZIA_REDIS_URL", "redis://localhost:6379/0")
    )
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = int(os.getenv("TRAZIA_WORKER_CONCURRENCY", "2"))
    job_timeout = 7300
    max_tries = 10
    allow_abort_jobs = True
    keep_result = 86400
