"""Law routes: collect / project / sync, plus a read route on one dossier."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine

router = APIRouter(tags=["laws"])


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
