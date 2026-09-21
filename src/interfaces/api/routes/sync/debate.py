"""Trigger routes for sittings — same shape as deputy.py."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_debates, build_project_debates
from src.config import Settings
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["sync"])


@router.post("/collect/debates")
async def collect_debates(
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N sittings"),
    since: date | None = Query(default=None, description="first sitting day, YYYY-MM-DD"),
    until: date | None = Query(default=None, description="last sitting day, YYYY-MM-DD"),
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_debates(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, limit=limit, since=since, until=until
        )
    return report.as_dict()


@router.post("/collect/debates/{uid}")
async def collect_one_debate(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_debates(settings, engine) as use_case:
        report = await use_case.execute_one(uid, legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/project/debates")
async def project_debates(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Re-run raw -> public. No network."""
    report = await build_project_debates(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/debates")
async def sync_debates(
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N sittings"),
    since: date | None = Query(default=None, description="first sitting day, YYYY-MM-DD"),
    until: date | None = Query(default=None, description="last sitting day, YYYY-MM-DD"),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Collect then project: sittings end up in public in one call."""
    leg = legislature or settings.an_legislature
    async with build_collect_debates(settings, engine) as use_case:
        collected = await use_case.execute(leg, limit=limit, since=since, until=until)
    projected = await build_project_debates(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


@router.post("/sync/debates/{uid}")
async def sync_one_debate(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    leg = legislature or settings.an_legislature
    async with build_collect_debates(settings, engine) as use_case:
        collected = await use_case.execute_one(uid, leg)
    projected = await build_project_debates(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}
