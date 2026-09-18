"""Ingestion history, read from raw.ingestion_run."""
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables
from src.interfaces.api.dependencies import get_engine

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_runs(
    entity_type: str | None = None,
    limit: int = Query(default=20, le=100),
    engine: AsyncEngine = Depends(get_engine),
) -> list[dict]:
    query = sa.select(tables.ingestion_run).order_by(
        tables.ingestion_run.c.id.desc()
    ).limit(limit)
    if entity_type:
        query = query.where(tables.ingestion_run.c.entity_type == entity_type)

    async with engine.connect() as connection:
        rows = (await connection.execute(query)).mappings().all()
    return [dict(row) for row in rows]


@router.get("/summary")
async def summary(engine: AsyncEngine = Depends(get_engine)) -> list[dict]:
    """Per-entity totals and last run."""
    query = (
        sa.select(
            tables.ingestion_run.c.entity_type,
            sa.func.count().label("runs"),
            sa.func.max(tables.ingestion_run.c.finished_at).label("last_finished_at"),
            sa.func.sum(tables.ingestion_run.c.created).label("created"),
            sa.func.sum(tables.ingestion_run.c.failed).label("failed"),
        )
        .group_by(tables.ingestion_run.c.entity_type)
        .order_by(tables.ingestion_run.c.entity_type)
    )
    async with engine.connect() as connection:
        rows = (await connection.execute(query)).mappings().all()
    return [dict(row) for row in rows]
