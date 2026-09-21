"""
Composition root — the only module that imports both `infrastructure` and
`application`. The API and the CLI both build their use cases here.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from src.application.use_cases.collect_agenda import CollectAgenda
from src.application.use_cases.collect_amendments import CollectAmendments
from src.application.use_cases.collect_ballots import CollectBallots
from src.application.use_cases.collect_debates import CollectDebates
from src.application.use_cases.collect_deputies import CollectDeputies
from src.application.use_cases.collect_law_texts import CollectLawTexts
from src.application.use_cases.collect_laws import CollectLaws
from src.application.use_cases.project_agenda import ProjectAgenda
from src.application.use_cases.project_amendments import ProjectAmendments
from src.application.use_cases.project_ballots import ProjectBallots
from src.application.use_cases.project_debates import ProjectDebates
from src.application.use_cases.project_deputies import ProjectDeputies
from src.application.use_cases.project_law_texts import ProjectLawTexts
from src.application.use_cases.project_laws import ProjectLaws
from src.application.use_cases.refresh_archives import RefreshArchives
from src.application.use_cases.sync_all import SyncAll
from src.config import Settings
from src.domain.ports.storage import RawStoragePort
from src.infrastructure.adapters.an_agenda_adapter import AnAgendaAdapter
from src.infrastructure.adapters.an_amendment_adapter import AnAmendmentAdapter
from src.infrastructure.adapters.an_ballot_adapter import AnBallotAdapter
from src.infrastructure.adapters.an_debate_adapter import AnDebateAdapter
from src.infrastructure.adapters.an_deputy_adapter import AnDeputyAdapter
from src.infrastructure.adapters.an_law_adapter import AnLawAdapter
from src.infrastructure.adapters.an_law_text_adapter import AnLawTextAdapter
from src.infrastructure.http.client import HttpClient
from src.infrastructure.persistence.engine import create_engine
from src.infrastructure.persistence.raw.agenda_repository import SqlRawAgendaRepository
from src.infrastructure.persistence.raw.amendment_repository import SqlRawAmendmentRepository
from src.infrastructure.persistence.raw.ballot_repository import SqlRawBallotRepository
from src.infrastructure.persistence.raw.debate_repository import SqlRawDebateRepository
from src.infrastructure.persistence.raw.deputy_repository import SqlRawDeputyRepository
from src.infrastructure.persistence.raw.ingestion_log_repository import (
    SqlIngestionLogRepository,
)
from src.infrastructure.persistence.raw.law_repository import SqlRawLawRepository
from src.infrastructure.persistence.raw.law_text_repository import SqlRawLawTextRepository
from src.infrastructure.persistence.serving.agenda_projection import SqlAgendaProjection
from src.infrastructure.persistence.serving.amendment_projection import SqlAmendmentProjection
from src.infrastructure.persistence.serving.ballot_projection import SqlBallotProjection
from src.infrastructure.persistence.serving.debate_projection import SqlDebateProjection
from src.infrastructure.persistence.serving.deputy_projection import SqlDeputyProjection
from src.infrastructure.persistence.serving.law_projection import SqlLawProjection
from src.infrastructure.persistence.serving.law_text_projection import SqlLawTextProjection
from src.infrastructure.storage.garage_s3_adapter import GarageS3Storage

# The biggest archives (amendments 340 MB, debates 55 MB) need a longer timeout.
LONG_TIMEOUT_S = 600.0


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


@dataclass
class Worker:
    """Every use case, wired once. `refresh` re-downloads archives, `dry_run` writes nothing."""

    collect_deputies: CollectDeputies
    collect_laws: CollectLaws
    collect_agenda: CollectAgenda
    collect_debates: CollectDebates
    collect_amendments: CollectAmendments
    collect_ballots: CollectBallots
    collect_law_texts: CollectLawTexts
    project_deputies: ProjectDeputies
    project_laws: ProjectLaws
    project_agenda: ProjectAgenda
    project_debates: ProjectDebates
    project_amendments: ProjectAmendments
    project_ballots: ProjectBallots
    project_law_texts: ProjectLawTexts
    refresh_archives: RefreshArchives
    sync_all: SyncAll


@asynccontextmanager
async def build_worker(
    settings: Settings,
    engine: AsyncEngine,
    *,
    dry_run: bool = False,
    refresh: bool = False,
) -> AsyncIterator[Worker]:
    storage = build_storage(settings)
    log = SqlIngestionLogRepository(engine)
    base = settings.an_base_url
    async with HttpClient(
        timeout_s=max(settings.http_timeout_s, LONG_TIMEOUT_S),
        max_attempts=settings.http_max_attempts,
    ) as http:
        deputies = AnDeputyAdapter(http, storage, base, refresh=refresh)
        laws = AnLawAdapter(http, storage, base, refresh=refresh)
        agenda = AnAgendaAdapter(http, storage, base, refresh=refresh)
        debates = AnDebateAdapter(http, storage, base, refresh=refresh)
        amendments = AnAmendmentAdapter(http, storage, base, refresh=refresh)
        ballots = AnBallotAdapter(http, storage, base, refresh=refresh)
        law_texts = AnLawTextAdapter(http, storage, refresh=refresh)

        agenda_repository = SqlRawAgendaRepository(engine)
        collect = dict(
            collect_deputies=CollectDeputies(
                source=deputies,
                repository=SqlRawDeputyRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
            collect_laws=CollectLaws(
                source=laws,
                repository=SqlRawLawRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
            collect_agenda=CollectAgenda(
                source=agenda, repository=agenda_repository, log_repository=log, dry_run=dry_run
            ),
            collect_debates=CollectDebates(
                source=debates,
                repository=SqlRawDebateRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
            collect_amendments=CollectAmendments(
                source=amendments,
                repository=SqlRawAmendmentRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
            collect_ballots=CollectBallots(
                source=ballots,
                repository=SqlRawBallotRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
            collect_law_texts=CollectLawTexts(
                source=law_texts,
                repository=SqlRawLawTextRepository(engine),
                log_repository=log,
                dry_run=dry_run,
            ),
        )
        project = dict(
            project_deputies=ProjectDeputies(projection=SqlDeputyProjection(engine)),
            project_laws=ProjectLaws(projection=SqlLawProjection(engine)),
            project_agenda=ProjectAgenda(projection=SqlAgendaProjection(engine)),
            project_debates=ProjectDebates(projection=SqlDebateProjection(engine)),
            project_amendments=ProjectAmendments(projection=SqlAmendmentProjection(engine)),
            project_ballots=ProjectBallots(projection=SqlBallotProjection(engine)),
            project_law_texts=ProjectLawTexts(projection=SqlLawTextProjection(engine)),
        )
        yield Worker(
            **collect,
            **project,
            refresh_archives=RefreshArchives(
                {
                    "deputies": deputies,
                    "laws": laws,
                    "agenda": agenda,
                    "debates": debates,
                    "amendments": amendments,
                    "ballots": ballots,
                }
            ),
            sync_all=SyncAll(agenda_repository=agenda_repository, **collect, **project),
        )
