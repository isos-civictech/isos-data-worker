"""Manual purge of `raw`, with a dry run to see what would go."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from src.composition import build_worker
from src.config import Settings
from src.interfaces.api.dependencies import get_engine, get_settings_dep
from src.interfaces.api.runs import RUNS

router = APIRouter(prefix="/purge", tags=["purge"])


@router.post("")
async def purge_raw(
    dry_run: bool = Query(default=True, description="count only, delete nothing"),
    days: int | None = Query(
        default=None, ge=1, description="retention; default RAW_RETENTION_DAYS"
    ),
    settings: Settings = Depends(get_settings_dep),
    engine: AsyncEngine = Depends(get_engine),
) -> dict:
    """Rows of `raw` already projected and older than the retention. A dry run by default."""

    async def work() -> dict:
        async with build_worker(settings, engine) as worker:
            return await worker.purge_raw.execute(dry_run=dry_run, days=days)

    return {"dry_run": dry_run, "rows": await RUNS.run("purge", work())}
