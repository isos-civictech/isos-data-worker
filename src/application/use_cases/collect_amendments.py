"""Collect amendments from the Assemblée nationale into `raw`, by batches."""

from datetime import date

from loguru import logger

from src.domain.ports.repositories.amendment_repository import AmendmentRepository
from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.sources.amendment_source import AmendmentSource
from src.domain.shared.results import SyncReport

ENTITY = "amendment"
BATCH_SIZE = 500


class CollectAmendments:
    def __init__(
        self,
        *,
        source: AmendmentSource,
        repository: AmendmentRepository,
        log_repository: IngestionLogRepository,
        dry_run: bool = False,
    ) -> None:
        self._source = source
        self._repository = repository
        self._log = log_repository
        self._dry_run = dry_run

    async def execute(
        self,
        legislature: int,
        *,
        dossier_uid: str | None = None,
        since: date | None = None,
        limit: int | None = None,
    ) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        source_url = getattr(self._source, "archive_url", lambda _: None)(legislature)
        run_id = await self._log.start_run(ENTITY, source_url=source_url)
        logger.info(
            "collect.start entity={} legislature={} dossier={} since={} limit={} dry_run={}",
            ENTITY,
            legislature,
            dossier_uid,
            since,
            limit,
            self._dry_run,
        )

        batch = []
        async for amendment in self._source.iter_all(
            legislature, dossier_uid=dossier_uid, since=since, limit=limit
        ):
            report.processed += 1
            if self._dry_run:
                report.skipped += 1
                continue
            batch.append(amendment)
            if len(batch) >= BATCH_SIZE:
                await self._flush(batch, run_id, report)
                batch = []
        await self._flush(batch, run_id, report)

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report

    async def _flush(self, batch, run_id: int, report: SyncReport) -> None:
        if not batch:
            return
        s3_key = getattr(self._source, "last_s3_key", None)
        try:
            outcome = await self._repository.save_batch(batch, run_id=run_id, s3_key=s3_key)
        except Exception:
            # A bad row sinks its batch, not the run; the uids are in the report.
            for a in batch:
                report.record_failure(a.uid)
            logger.exception("collect.batch_failed entity={} size={}", ENTITY, len(batch))
            return
        report.created += outcome.created
        report.updated += outcome.updated
