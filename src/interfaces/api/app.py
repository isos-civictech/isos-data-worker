"""
FastAPI application. Port 8001 matches the Kubernetes Service in isos-ops.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.composition import build_engine
from src.config import get_settings
from src.interfaces.api.routes import health, home, jobs, pipeline
from src.interfaces.api.routes.sync import agenda, amendment, ballot, law, law_text
from src.logging_setup import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    app.state.settings = settings
    app.state.engine = build_engine(settings)
    try:
        yield
    finally:
        await app.state.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="isos-data-worker",
        description="Collects Assemblée nationale open data into the raw schema.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(home.router)
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(pipeline.router)
    app.include_router(agenda.router)
    app.include_router(law.router)
    app.include_router(amendment.router)
    app.include_router(ballot.router)
    app.include_router(law_text.router)
    return app
