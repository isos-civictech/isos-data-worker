"""
One long run at a time, and a way to stop it. Every long route goes through
`RUNS.run`, so `POST /cancel` can reach whichever run is in progress.
"""

import asyncio
from collections.abc import Awaitable

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables


class RunRegistry:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.name: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run(self, name: str, work: Awaitable):
        """Run `work`, refused with 409 while another run is in progress."""
        if self.running:
            work.close()
            raise HTTPException(status_code=409, detail=f"{self.name} is already running")
        task = asyncio.ensure_future(work)
        self._task, self.name = task, name
        try:
            return await task
        except asyncio.CancelledError:
            if task.cancelled() and not asyncio.current_task().cancelling():
                raise HTTPException(status_code=409, detail=f"{name} was cancelled") from None
            raise
        finally:
            if self._task is task:
                self._task = self.name = None

    async def cancel(self, engine: AsyncEngine) -> str | None:
        """Stop the current run and close its unfinished ingestion rows. Returns its name."""
        task, name = self._task, self.name
        if task is None or task.done():
            return None
        task.cancel()
        await asyncio.wait([task])
        run = tables.ingestion_run
        async with engine.begin() as connection:
            await connection.execute(
                sa.update(run)
                .where(run.c.status == "running")
                .values(status="failed", finished_at=sa.func.now())
            )
        return name


RUNS = RunRegistry()
