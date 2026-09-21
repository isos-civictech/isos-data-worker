"""Collect the sittings agenda from the Assemblée nationale into `raw`."""

from datetime import date

from loguru import logger

from src.domain.ports.repositories.agenda_repository import AgendaRepository
from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.sources.agenda_source import AgendaSource
from src.domain.shared.results import SyncReport

ENTITY = "agenda"


class CollectAgenda:
    def __init__(
        self,
        *,
        source: AgendaSource,
        repository: AgendaRepository,
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
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        source_url = getattr(self._source, "archive_url", lambda _: None)(legislature)
        run_id = await self._log.start_run(ENTITY, source_url=source_url)
        logger.info(
            "collect.start entity={} legislature={} limit={} since={} until={} dry_run={}",
            ENTITY,
            legislature,
            limit,
            since,
            until,
            self._dry_run,
        )

        items = await self._source.fetch_all(legislature, limit=limit, since=since, until=until)
        s3_key = getattr(self._source, "last_s3_key", None)

        for item in items:
            report.processed += 1
            if self._dry_run:
                report.skipped += 1
                continue
            try:
                outcome = await self._repository.save(item, run_id=run_id, s3_key=s3_key)
            except Exception:
                report.record_failure(item.uid)
                logger.exception("collect.item_failed entity={} uid={}", ENTITY, item.uid)
                continue
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report
