"""Cola local intercambiable; la base de datos conserva el estado y los resultados."""

import asyncio
from typing import Awaitable, Callable, Protocol


class JobQueue(Protocol):
    async def enqueue(self, job_id: str) -> None: ...
    async def cancel(self, job_id: str) -> None: ...
    async def close(self) -> None: ...


class ProcessQueue:
    def __init__(self, execute: Callable[[str], Awaitable[None]], concurrency: int = 2):
        self.execute = execute
        self.limit = asyncio.Semaphore(concurrency)
        self.tasks: dict[str, asyncio.Task] = {}

    async def enqueue(self, job_id: str):
        if job_id in self.tasks:
            return

        async def run():
            async with self.limit:
                await self.execute(job_id)

        task = asyncio.create_task(run(), name=f"trazia:{job_id}")
        self.tasks[job_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(job_id, None))

    async def cancel(self, job_id: str):
        if task := self.tasks.get(job_id):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
