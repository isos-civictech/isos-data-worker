"""Amendment routes: collect, plus a read route listing one dossier's amendments."""

from datetime import date

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_amendments, build_project_amendments
from src.config import Settings
from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["amendments"])


@router.post("/collect/amendments")
async def collect_amendments(
    legislature: int | None = None,
    dossier: str | None = Query(default=None, description="one dossier only (DLR…)"),
    since: date | None = Query(default=None, description="deposited on or after, YYYY-MM-DD"),
    limit: int | None = None,
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """The archive is ~340 MB: a full run takes a few minutes."""
    async with build_collect_amendments(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, dossier_uid=dossier, since=since, limit=limit
        )
    return report.as_dict()


@router.post("/project/amendments")
async def project_amendments(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Needs public.law and public.deputy: run /sync/laws and /sync/deputies first."""
    report = await build_project_amendments(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/amendments")
async def sync_amendments(
    legislature: int | None = None,
    dossier: str | None = Query(default=None),
    since: date | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    leg = legislature or settings.an_legislature
    async with build_collect_amendments(settings, engine) as use_case:
        collected = await use_case.execute(leg, dossier_uid=dossier, since=since)
    projected = await build_project_amendments(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


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
