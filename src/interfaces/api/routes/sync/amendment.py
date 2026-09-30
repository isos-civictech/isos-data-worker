"""Amendment routes: collect, plus a read route listing one dossier's amendments."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine

router = APIRouter(tags=["amendments"])


@router.get("/laws/{uid}/amendments")
async def law_amendments(
    uid: str,
    limit: int = Query(default=100, ge=1, le=1000),
    engine: AsyncEngine = Depends(get_engine),
) -> list[dict]:
    """Amendments of one dossier, newest first, straight from raw (bodies omitted)."""
    t = raw.amendment
    query = (
        sa.select(
            t.c.uid,
            t.c.number,
            t.c.examined_by,
            t.c.author_type,
            t.c.deputy_uid,
            t.c.signatories,
            t.c.division_title,
            t.c.division_position,
            t.c.state,
            t.c.sort,
            t.c.deposited_at,
        )
        .where(t.c.dossier_uid == uid)
        .order_by(t.c.deposited_at.desc(), t.c.number.desc())
        .limit(limit)
    )
    async with engine.connect() as connection:
        return [dict(r) for r in (await connection.execute(query)).mappings().all()]
