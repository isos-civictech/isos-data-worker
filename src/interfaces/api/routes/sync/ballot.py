"""Ballot routes: collect / project / sync, plus one deputy's voting record from raw."""

from datetime import date

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_ballots, build_project_ballots
from src.config import Settings
from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["ballots"])


@router.post("/collect/ballots")
async def collect_ballots(
    legislature: int | None = None,
    since: date | None = Query(default=None, description="first vote day, YYYY-MM-DD"),
    until: date | None = Query(default=None, description="last vote day, YYYY-MM-DD"),
    limit: int | None = None,
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_ballots(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, since=since, until=until, limit=limit
        )
    return report.as_dict()


@router.post("/project/ballots")
async def project_ballots(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Needs agenda, laws, deputies and amendments in public first."""
    report = await build_project_ballots(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/ballots")
async def sync_ballots(
    legislature: int | None = None,
    since: date | None = Query(default=None),
    until: date | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    leg = legislature or settings.an_legislature
    async with build_collect_ballots(settings, engine) as use_case:
        collected = await use_case.execute(leg, since=since, until=until)
    projected = await build_project_ballots(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


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
