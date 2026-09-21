"""
Agenda routes: collect / project / sync, plus two read routes that answer
"what is on today" and "what comes next" straight from raw.
"""

from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_agenda, build_project_agenda
from src.config import Settings
from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["agenda"])


@router.post("/collect/agenda")
async def collect_agenda(
    legislature: int | None = None,
    limit: int | None = None,
    since: date | None = Query(default=None, description="first sitting day, YYYY-MM-DD"),
    until: date | None = Query(default=None, description="last sitting day, YYYY-MM-DD"),
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_agenda(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, limit=limit, since=since, until=until
        )
    return report.as_dict()


@router.post("/project/agenda")
async def project_agenda(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    report = await build_project_agenda(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/agenda")
async def sync_agenda(
    legislature: int | None = None,
    since: date | None = Query(default=None),
    until: date | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Collect then project: scheduled, held and cancelled sittings land in public.debate."""
    leg = legislature or settings.an_legislature
    async with build_collect_agenda(settings, engine) as use_case:
        collected = await use_case.execute(leg, since=since, until=until)
    projected = await build_project_agenda(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


# ── read routes ───────────────────────────────────────────────────────────────


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
