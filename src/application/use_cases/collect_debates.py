"""
Collect sittings from the Assemblée nationale into `raw`.

Same shape as collect_deputies: ports only, one save per sitting, a failing
record is counted and logged and the run goes on.
"""

from datetime import date

from loguru import logger

from src.domain.ports.repositories.debate_repository import DebateRepository
from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.sources.debate_source import DebateSource
from src.domain.shared.results import SyncReport

ENTITY = "debate"


class CollectDebates:
    def __init__(
        self,
        *,
        source: DebateSource,
        repository: DebateRepository,
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

        debates = await self._source.fetch_all(legislature, limit=limit, since=since, until=until)
        s3_key = getattr(self._source, "last_s3_key", None)

        for debate in debates:
            report.processed += 1
            if self._dry_run:
                report.skipped += 1
                continue
            try:
                outcome = await self._repository.save(debate, run_id=run_id, s3_key=s3_key)
            except Exception:
                report.record_failure(debate.uid)
                logger.exception("collect.item_failed entity={} uid={}", ENTITY, debate.uid)
                continue
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report

    async def execute_one(self, uid: str, legislature: int) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        run_id = await self._log.start_run(ENTITY)

        debate = await self._source.fetch_by_uid(uid, legislature)
        if debate is None:
            logger.warning("collect.not_found entity={} uid={}", ENTITY, uid)
            report.finish()
            await self._log.finish_run(run_id, report)
            return report

        report.processed = 1
        try:
            outcome = await self._repository.save(
                debate, run_id=run_id, s3_key=getattr(self._source, "last_s3_key", None)
            )
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)
        except Exception:
            report.record_failure(uid)
            logger.exception("collect.item_failed entity={} uid={}", ENTITY, uid)

        report.finish()
        await self._log.finish_run(run_id, report)
        return report
