"""Law routes: collect / project / sync, plus a read route on one dossier."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_laws, build_project_laws
from src.config import Settings
from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["laws"])


@router.post("/collect/laws")
async def collect_laws(
    legislature: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_laws(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(legislature or settings.an_legislature, limit=limit)
    return report.as_dict()


@router.post("/collect/laws/{uid}")
async def collect_one_law(
    uid: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    async with build_collect_laws(settings, engine) as use_case:
        report = await use_case.execute_one(uid, legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/project/laws")
async def project_laws(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    report = await build_project_laws(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/laws")
async def sync_laws(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Collect then project. Run after /sync/agenda so debate_law can link sittings."""
    leg = legislature or settings.an_legislature
    async with build_collect_laws(settings, engine) as use_case:
        collected = await use_case.execute(leg)
    projected = await build_project_laws(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


@router.get("/laws/{uid}")
async def law_detail(uid: str, engine: AsyncEngine = Depends(get_engine)) -> dict:
    """One dossier with its stages, straight from raw."""
    async with engine.connect() as connection:
        law = (
            (await connection.execute(sa.select(raw.law).where(raw.law.c.dossier_uid == uid)))
            .mappings()
            .first()
        )
        if law is None:
            raise HTTPException(status_code=404, detail=f"unknown dossier {uid}")
        stages = (
            (
                await connection.execute(
                    sa.select(raw.law_stage)
                    .where(raw.law_stage.c.dossier_uid == uid)
                    .order_by(raw.law_stage.c.position)
                )
            )
            .mappings()
            .all()
        )
    return {
        "uid": law["dossier_uid"],
        "title": law["title"],
        "procedure": law["procedure_label"],
        "withdrawn": law["withdrawn"],
        "initiators": law["initiator_uids"],
        "stages": [
            {
                "code": s["code"],
                "label": s["label"],
                "started_at": s["started_at"],
                "concluded_at": s["concluded_at"],
                "decision": s["decision"],
                "texte_uid": s["texte_uid"],
                "sittings": s["sitting_refs"],
            }
            for s in stages
        ],
    }
