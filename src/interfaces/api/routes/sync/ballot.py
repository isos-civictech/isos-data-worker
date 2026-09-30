"""Ballot routes: collect / project / sync, plus one deputy's voting record from raw."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine

router = APIRouter(tags=["ballots"])


@router.get("/deputies/{uid}/votes")
async def deputy_votes(
    uid: str,
    limit: int = Query(default=50, ge=1, le=500),
    engine: AsyncEngine = Depends(get_engine),
) -> list[dict]:
    """One deputy's last votes, newest first, straight from raw."""
    b, v = raw.ballot, raw.ballot_vote
    query = (
        sa.select(
            b.c.uid, b.c.date, b.c.title, b.c.result, v.c.position, v.c.corrected_position,
            v.c.by_delegation,
        )
        .select_from(v.join(b, b.c.uid == v.c.ballot_uid))
        .where(v.c.deputy_uid == uid)
        .order_by(b.c.date.desc(), b.c.number.desc())
        .limit(limit)
    )  # fmt: skip
    async with engine.connect() as connection:
        return [dict(r) for r in (await connection.execute(query)).mappings().all()]
