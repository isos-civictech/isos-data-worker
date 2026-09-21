"""
Trigger routes — same use cases as the CLI, via the composition root.

  /collect/…   Assemblée nationale -> raw          (network)
  /project/…   raw -> public                       (SQL only)
  /sync/…      both, in order — what "fetch the deputies" means end to end
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_deputies, build_project_deputies
from src.config import Settings
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["sync"])


@router.post("/collect/deputies")
async def collect_deputies(
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N deputies"),
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_deputies(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(legislature or settings.an_legislature, limit=limit)
    return report.as_dict()


@router.post("/collect/deputies/{uid}")
async def collect_one_deputy(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_deputies(settings, engine) as use_case:
        report = await use_case.execute_one(uid, legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/project/deputies")
async def project_deputies(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Re-run raw -> public. No network: safe to call after a mapping fix."""
    report = await build_project_deputies(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/deputies")
async def sync_deputies(
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N deputies"),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Collect then project: the deputies end up in public in one call."""
    leg = legislature or settings.an_legislature
    async with build_collect_deputies(settings, engine) as use_case:
        collected = await use_case.execute(leg, limit=limit)
    projected = await build_project_deputies(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


@router.post("/sync/deputies/{uid}")
async def sync_one_deputy(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """One deputy, added or updated, all the way to public."""
    leg = legislature or settings.an_legislature
    async with build_collect_deputies(settings, engine) as use_case:
        collected = await use_case.execute_one(uid, leg)
    projected = await build_project_deputies(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}
