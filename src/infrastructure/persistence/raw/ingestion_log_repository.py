"""
Run-level audit over `raw.ingestion_run`. Per-entity lines are written by each
entity's repository, inside its own transaction.
"""
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.raw import tables


class SqlIngestionLogRepository(IngestionLogRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def start_run(self, entity_type: str, source_url: str | None = None) -> int:
        statement = (
            sa.insert(tables.ingestion_run)
            .values(entity_type=entity_type, source_url=source_url, status="running")
            .returning(tables.ingestion_run.c.id)
        )
        async with self._engine.begin() as connection:
            return (await connection.execute(statement)).scalar_one()

    async def finish_run(self, run_id: int, report: SyncReport) -> None:
        statement = (
            sa.update(tables.ingestion_run)
            .where(tables.ingestion_run.c.id == run_id)
            .values(
                status="ok" if report.ok else "failed",
                processed=report.processed,
                created=report.created,
                updated=report.updated,
                skipped=report.skipped,
                failed=report.failed,
                finished_at=sa.func.now(),
            )
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)
