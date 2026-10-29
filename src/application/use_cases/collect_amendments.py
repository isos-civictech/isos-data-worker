"""Collect amendments from the Assemblée nationale into `raw`, by batches."""

from datetime import date

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "amendment"
BATCH_SIZE = 500


class CollectAmendments(CollectUseCase):
    entity = ENTITY

    async def execute(
        self,
        legislature: int,
        *,
        dossier_uid: str | None = None,
        since: date | None = None,
        limit: int | None = None,
    ) -> SyncReport:
        report, run_id = await self._begin(legislature)
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
        return await self._end(report, run_id)

    async def _flush(self, batch, run_id: int, report: SyncReport) -> None:
        if not batch:
            return
        try:
            outcome = await self._repository.save_batch(batch, run_id=run_id, s3_key=self._s3_key)
        except Exception:
            # A bad row sinks its batch, not the run; the uids are in the report.
            for a in batch:
                report.record_failure(a.uid)
            logger.exception("collect.batch_failed entity={} size={}", ENTITY, len(batch))
            return
        report.created += outcome.created
        report.updated += outcome.updated
