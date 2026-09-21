"""
Agenda routes: collect / project / sync, plus two read routes that answer
"what is on today" and "what comes next" straight from raw.
"""

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine

router = APIRouter(tags=["agenda"])


async def _sittings(engine: AsyncEngine, since: datetime, until: datetime) -> list[dict]:
    query = (
        sa.select(raw.agenda_item)
        .where(raw.agenda_item.c.start_at >= since, raw.agenda_item.c.start_at < until)
        .order_by(raw.agenda_item.c.start_at)
    )
    async with engine.connect() as connection:
        sittings = (await connection.execute(query)).mappings().all()
        out = []
        for s in sittings:
            points = (
                (
                    await connection.execute(
                        sa.select(raw.agenda_point)
                        .where(raw.agenda_point.c.agenda_uid == s["uid"])
                        .order_by(raw.agenda_point.c.position)
                    )
                )
                .mappings()
                .all()
            )
            out.append(
                {
                    "uid": s["uid"],
                    "start_at": s["start_at"],
                    "end_at": s["end_at"],
                    "state": s["state"],
                    "session_rank": s["session_rank"],
                    "compte_rendu_uid": s["compte_rendu_uid"],
                    "points": [
                        {"title": p["title"], "kind": p["kind"], "dossier_refs": p["dossier_refs"]}
                        for p in points
                    ],
                }
            )
    return out


@router.get("/agenda/today")
async def agenda_today(engine: AsyncEngine = Depends(get_engine)) -> list[dict]:
    """Sittings starting today (UTC day)."""
    start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return await _sittings(engine, start, start + timedelta(days=1))


@router.get("/agenda/upcoming")
async def agenda_upcoming(
    days: int = Query(default=14, ge=1, le=90), engine: AsyncEngine = Depends(get_engine)
) -> list[dict]:
    """Sittings from now until `days` ahead."""
    now = datetime.now(tz=UTC)
    return await _sittings(engine, now, now + timedelta(days=days))
