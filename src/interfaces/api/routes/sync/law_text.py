"""Law text routes: collect / project / sync, plus one article across its versions."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_collect_law_texts, build_project_law_texts
from src.config import Settings
from src.infrastructure.persistence.raw import tables as raw
from src.interfaces.api.dependencies import get_engine, get_settings_dep

router = APIRouter(tags=["law texts"])

KIND_ORDER = sa.case(
    (raw.law_text.c.kind == "deposited", 0),
    (raw.law_text.c.kind == "commission", 1),
    else_=2,
)


@router.post("/collect/law-texts")
async def collect_law_texts(
    legislature: int | None = None,
    dossier: str | None = Query(default=None, description="one dossier only (DLR…)"),
    uid: str | None = Query(default=None, description="one text (PRJLANR5L17B2681)"),
    limit: int | None = None,
    dry_run: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Incremental: only texts never fetched are requested (one HTTP call each)."""
    async with build_collect_law_texts(settings, engine, dry_run=dry_run) as use_case:
        report = await use_case.execute(
            legislature or settings.an_legislature, dossier_uid=dossier, texte_uid=uid, limit=limit
        )
    return report.as_dict()


@router.post("/project/law-texts")
async def project_law_texts(
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    report = await build_project_law_texts(engine).execute(legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/law-texts")
async def sync_law_texts(
    legislature: int | None = None,
    dossier: str | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    leg = legislature or settings.an_legislature
    async with build_collect_law_texts(settings, engine) as use_case:
        collected = await use_case.execute(leg, dossier_uid=dossier)
    projected = await build_project_law_texts(engine).execute(leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


@router.get("/laws/{uid}/articles/{article_ref}")
async def article_versions(
    uid: str, article_ref: str, engine: AsyncEngine = Depends(get_engine)
) -> list[dict]:
    """
    One article of a dossier along the navette: deposited, then commission,
    then adopted… Each version lists the amendments that targeted it; the
    adopted ones explain the difference with the next version.
    """
    t, a, am, doc = raw.law_text, raw.law_article, raw.amendment, raw.law_texte
    query = (
        sa.select(t.c.texte_uid, t.c.kind, a.c.is_new, a.c.mention, a.c.content)
        .select_from(
            a.join(t, t.c.texte_uid == a.c.texte_uid).outerjoin(doc, doc.c.uid == t.c.texte_uid)
        )
        .where(t.c.dossier_uid == uid, a.c.article_ref == article_ref)
        # Same order as public.law_text.position.
        .order_by(doc.c.deposited_at.nulls_last(), KIND_ORDER, t.c.texte_uid)
    )
    async with engine.connect() as connection:
        versions = [
            {"position": position, **r}
            for position, r in enumerate((await connection.execute(query)).mappings().all(), 1)
        ]
        for v in versions:
            amendments = (
                await connection.execute(
                    sa.select(am.c.uid, am.c.number, am.c.author_type, am.c.deputy_uid, am.c.sort)
                    .where(am.c.texte_uid == v["texte_uid"], am.c.division_title == article_ref)
                    .order_by(am.c.number)
                )
            ).mappings()
            v["amendments"] = [dict(x) for x in amendments]
    return versions
