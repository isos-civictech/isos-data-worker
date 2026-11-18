"""
Initialisation of an empty database. Once the deputies are in, the database
counts as initialised and the first fill is refused: later runs enrich it.
"""

import asyncio

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_worker
from src.config import Settings
from src.infrastructure.persistence.raw import tables
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(prefix="/init", tags=["init"])

_running = asyncio.Lock()


async def is_initialised(engine: AsyncEngine) -> bool:
    query = sa.select(sa.exists().where(tables.deputy.c.id.isnot(None)))
    async with engine.connect() as connection:
        return bool((await connection.execute(query)).scalar())


@router.get("")
async def status(engine: AsyncEngine = Depends(get_engine)) -> dict:
    return {"initialised": await is_initialised(engine), "running": _running.locked()}


@router.post("")
async def initialise(
    legislature: int | None = None,
    refresh: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """First fill of an empty database. 409 when it already holds data or a fill is running."""
    if _running.locked():
        raise HTTPException(status_code=409, detail="an initialisation is already running")
    async with _running:
        if await is_initialised(engine):
            raise HTTPException(status_code=409, detail="the database is already initialised")
        async with build_worker(settings, engine, refresh=refresh) as worker:
            return await worker.init_database.execute(legislature or settings.an_legislature)
