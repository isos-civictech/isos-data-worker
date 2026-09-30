"""
The pipeline, dataset by dataset or all at once. Every route answers with the
run report(s). Long runs (amendments, law texts) take minutes: call them from
a job, not from a page.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_worker
from src.config import Settings
from src.interfaces.api.dependencies import get_engine, get_settings_dep
from src.interfaces.dispatch import DATASETS, Selection, collect, project

router = APIRouter(tags=["pipeline"])


def _check(dataset: str) -> None:
    if dataset not in DATASETS:
        raise HTTPException(status_code=404, detail=f"unknown dataset, expected one of {DATASETS}")


@router.post("/collect/{dataset}")
async def collect_dataset(
    dataset: str,
    legislature: int | None = None,
    limit: int | None = Query(default=None, description="stop after N items"),
    uid: str | None = Query(default=None, description="one item only (PA…, DLR…, CRSAN…, VTAN…)"),
    dossier: str | None = Query(default=None, description="one dossier (amendments, law-texts)"),
    since: date | None = Query(default=None, description="YYYY-MM-DD"),
    until: date | None = Query(default=None, description="YYYY-MM-DD"),
    dry_run: bool = False,
    refresh: bool = Query(default=False, description="re-download the archive instead of S3"),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Assemblée nationale → raw. The archive comes from our S3 when it is there."""
    _check(dataset)
    selection = Selection(limit=limit, uid=uid, dossier=dossier, since=since, until=until)
    async with build_worker(settings, engine, dry_run=dry_run, refresh=refresh) as worker:
        report = await collect(worker, dataset, legislature or settings.an_legislature, selection)
    return report.as_dict()


@router.post("/project/{dataset}")
async def project_dataset(
    dataset: str,
    legislature: int | None = None,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """raw → public. No network: safe to re-run after a mapping fix."""
    _check(dataset)
    async with build_worker(settings, engine) as worker:
        report = await project(worker, dataset, legislature or settings.an_legislature)
    return report.as_dict()


@router.post("/sync/all")
async def sync_all(
    legislature: int | None = None,
    debates: int | None = Query(
        default=None,
        ge=1,
        description="scope: every deputy, then only the N latest sittings and what they touch",
    ),
    refresh: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Everything, in dependency order. Without `debates`, the whole legislature."""
    async with build_worker(settings, engine, refresh=refresh) as worker:
        return await worker.sync_all.execute(
            legislature or settings.an_legislature, debates=debates
        )


@router.post("/sync/{dataset}")
async def sync_dataset(
    dataset: str,
    legislature: int | None = None,
    dossier: str | None = Query(default=None),
    since: date | None = Query(default=None),
    until: date | None = Query(default=None),
    refresh: bool = False,
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Collect then project one dataset."""
    _check(dataset)
    leg = legislature or settings.an_legislature
    async with build_worker(settings, engine, refresh=refresh) as worker:
        collected = await collect(
            worker, dataset, leg, Selection(dossier=dossier, since=since, until=until)
        )
        projected = await project(worker, dataset, leg)
    return {"collect": collected.as_dict(), "project": projected.as_dict()}


@router.post("/refresh")
async def refresh_archives(
    legislature: int | None = None,
    datasets: list[str] | None = Query(
        default=None, description="deputies laws agenda debates amendments ballots (all if empty)"
    ),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Re-download the Assemblée archives into S3. The database is not touched."""
    async with build_worker(settings, engine) as worker:
        unknown = set(datasets or []) - set(worker.refresh_archives.datasets)
        if unknown:
            raise HTTPException(status_code=404, detail=f"unknown datasets {sorted(unknown)}")
        return await worker.refresh_archives.execute(
            legislature or settings.an_legislature, datasets
        )
