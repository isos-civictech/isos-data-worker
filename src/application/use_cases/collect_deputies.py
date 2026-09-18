"""
Collect deputies from the Assemblée nationale into `raw`.

Depends on ports only. Groups are stored before deputies (mandates reference
them by uid). A failing record is counted and logged; the run goes on.
"""
from loguru import logger

from src.domain.ports.repositories.deputy_repository import DeputyRepository
from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.sources.deputy_source import DeputySource
from src.domain.shared.results import SyncReport

ENTITY = "deputy"


class CollectDeputies:
    def __init__(
        self,
        *,
        source: DeputySource,
        repository: DeputyRepository,
        log_repository: IngestionLogRepository,
        dry_run: bool = False,
    ) -> None:
        self._source = source
        self._repository = repository
        self._log = log_repository
        self._dry_run = dry_run

    async def execute(self, legislature: int, limit: int | None = None) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        source_url = getattr(self._source, "archive_url", lambda _: None)(legislature)
        run_id = await self._log.start_run(ENTITY, source_url=source_url)

        logger.info(
            "collect.start entity={} legislature={} limit={} dry_run={}",
            ENTITY,
            legislature,
            limit,
            self._dry_run,
        )

        groups = await self._source.fetch_political_groups(legislature)
        if not self._dry_run:
            await self._repository.save_political_groups(groups)
        logger.info("collect.groups count={}", len(groups))

        deputies = await self._source.fetch_all(legislature, limit=limit)
        checksum = getattr(self._source, "last_checksum", None)

        for deputy in deputies:
            report.processed += 1

            if self._dry_run:
                report.skipped += 1
                continue

            try:
                outcome = await self._repository.save(
                    deputy,
                    legislature=legislature,
                    run_id=run_id,
                    source_url=source_url,
                    checksum=checksum,
                )
            except Exception:
                report.record_failure(deputy.uid)
                logger.exception("collect.item_failed entity={} uid={}", ENTITY, deputy.uid)
                continue

            if outcome.created:
                report.created += 1
            else:
                report.updated += 1

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report

    async def execute_one(self, uid: str, legislature: int) -> SyncReport:
        """Replay a single deputy — what POST /collect/deputies/{uid} calls."""
        report = SyncReport(entity=ENTITY)
        run_id = await self._log.start_run(ENTITY)

        deputy = await self._source.fetch_by_uid(uid, legislature)
        if deputy is None:
            logger.warning("collect.not_found entity={} uid={}", ENTITY, uid)
            report.finish()
            await self._log.finish_run(run_id, report)
            return report

        report.processed = 1
        try:
            outcome = await self._repository.save(
                deputy, legislature=legislature, run_id=run_id
            )
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)
        except Exception:
            report.record_failure(uid)
            logger.exception("collect.item_failed entity={} uid={}", ENTITY, uid)

        report.finish()
        await self._log.finish_run(run_id, report)
        return report
