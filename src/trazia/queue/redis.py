import asyncio

from arq.connections import RedisSettings, create_pool
from arq.jobs import Job


class RedisQueue:
    def __init__(self, pool):
        self.pool = pool

    @classmethod
    async def connect(cls, url: str):
        return cls(await create_pool(RedisSettings.from_dsn(url)))

    async def enqueue(self, job_id: str):
        await self.pool.enqueue_job("execute_job", job_id, _job_id=job_id)

    async def cancel(self, job_id: str):
        try:
            await Job(job_id, self.pool).abort(timeout=2)
        except (TimeoutError, asyncio.TimeoutError):
            # La cancelación persistida se comprueba antes de publicar incluso sin ACK de Redis.
            pass

    async def close(self):
        await self.pool.aclose()
