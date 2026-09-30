import sqlalchemy as sa
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from src.interfaces.api.dependencies import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness."""
    return {"status": "ok", "service": "isos-data-worker"}


@router.get("/health/db")
async def health_db(engine: AsyncEngine = Depends(get_engine)):
    """Readiness — kept separate so a Postgres blip never restarts the pod."""
    try:
        async with engine.connect() as connection:
            await connection.execute(sa.text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "unavailable", "detail": str(exc)})
    return {"status": "ok"}
