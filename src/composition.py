"""
Composition root — the only module that imports both `infrastructure` and
`application`. The API and the CLI both build their use cases here.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine

from src.application.use_cases.collect_debates import CollectDebates
from src.application.use_cases.collect_deputies import CollectDeputies
from src.application.use_cases.project_debates import ProjectDebates
from src.application.use_cases.project_deputies import ProjectDeputies
from src.config import Settings
from src.domain.ports.storage import RawStoragePort
from src.infrastructure.adapters.an_debate_adapter import AnDebateAdapter
from src.infrastructure.adapters.an_deputy_adapter import AnDeputyAdapter
from src.infrastructure.http.client import HttpClient
from src.infrastructure.persistence.engine import create_engine
from src.infrastructure.persistence.raw.debate_repository import SqlRawDebateRepository
from src.infrastructure.persistence.raw.deputy_repository import SqlRawDeputyRepository
from src.infrastructure.persistence.raw.ingestion_log_repository import (
    SqlIngestionLogRepository,
)
from src.infrastructure.persistence.serving.debate_projection import SqlDebateProjection
from src.infrastructure.persistence.serving.deputy_projection import SqlDeputyProjection
from src.infrastructure.storage.garage_s3_adapter import GarageS3Storage


def build_engine(settings: Settings) -> AsyncEngine:
    return create_engine(settings.database_url)


def build_storage(settings: Settings) -> RawStoragePort:
    if not settings.s3_enabled:
        raise RuntimeError(
            "S3 is not configured. Set S3_ENDPOINT, S3_ACCESS_KEY and "
            "S3_SECRET_KEY — `docker compose up -d garage garage-bootstrap` "
            "starts a local Garage with the values from .env."
        )
    return GarageS3Storage(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket_raw,
    )


@asynccontextmanager
async def build_collect_deputies(
    settings: Settings,
    engine: AsyncEngine,
    *,
    dry_run: bool = False,
) -> AsyncIterator[CollectDeputies]:
    storage = build_storage(settings)
    async with HttpClient(
        timeout_s=settings.http_timeout_s,
        max_attempts=settings.http_max_attempts,
    ) as http:
        yield CollectDeputies(
            source=AnDeputyAdapter(http, storage, settings.an_base_url),
            repository=SqlRawDeputyRepository(engine),
            log_repository=SqlIngestionLogRepository(engine),
            dry_run=dry_run,
        )


def build_project_deputies(engine: AsyncEngine) -> ProjectDeputies:
    return ProjectDeputies(projection=SqlDeputyProjection(engine))


@asynccontextmanager
async def build_collect_debates(
    settings: Settings,
    engine: AsyncEngine,
    *,
    dry_run: bool = False,
) -> AsyncIterator[CollectDebates]:
    storage = build_storage(settings)
    async with HttpClient(
        # The Syceron archive is ~55 MB: give it more room than the default.
        timeout_s=max(settings.http_timeout_s, 120.0),
        max_attempts=settings.http_max_attempts,
    ) as http:
        yield CollectDebates(
            source=AnDebateAdapter(http, storage, settings.an_base_url),
            repository=SqlRawDebateRepository(engine),
            log_repository=SqlIngestionLogRepository(engine),
            dry_run=dry_run,
        )


def build_project_debates(engine: AsyncEngine) -> ProjectDebates:
    return ProjectDebates(projection=SqlDebateProjection(engine))
