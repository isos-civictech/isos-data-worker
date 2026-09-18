"""Trigger routes — same use cases as the CLI, via the composition root."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_deputies
from src.config import Settings
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(prefix="/collect", tags=["collect"])


@router.post("/deputies")
async def collect_deputies(
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N deputies"),
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_deputies(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, limit=limit
        )
    return report.as_dict()


@router.post("/deputies/{uid}")
async def collect_one_deputy(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_deputies(settings, engine) as use_case:
        report = await use_case.execute_one(
            uid, legislature or settings.an_legislature
        )
    return report.as_dict()
