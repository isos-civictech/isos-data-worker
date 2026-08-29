"""
Ingestion audit — implementation over `raw.ingestion_run` and `raw.ingestion_log`.

The run rows are written in their own short transaction: a run must stay
traceable even when the entity that follows fails and rolls back. The per-entity
`record()` calls, on the other hand, run INSIDE the entity's transaction — an
audit line for a row that got rolled back would be a lie.
"""
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

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

    async def record(
        self,
        *,
        run_id: int,
        entity_type: str,
        entity_uid: str,
        source_url: str | None = None,
        s3_key: str | None = None,
        checksum: str | None = None,
    ) -> None:
        raise NotImplementedError(
            "Use record_in(connection, ...): this write belongs inside the "
            "entity's own transaction."
        )

    @staticmethod
    async def record_in(
        connection: AsyncConnection,
        *,
        run_id: int,
        entity_type: str,
        entity_uid: str,
        source_url: str | None = None,
        s3_key: str | None = None,
        checksum: str | None = None,
    ) -> None:
        """Trace one ingested entity, on the caller's connection."""
        await connection.execute(
            sa.insert(tables.ingestion_log).values(
                run_id=run_id,
                entity_type=entity_type,
                entity_uid=entity_uid,
                source_url=source_url,
                s3_key=s3_key,
                checksum=checksum,
            )
        )
