"""Collect legislative dossiers from the Assemblée nationale into `raw`."""

from loguru import logger

from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.repositories.law_repository import LawRepository
from src.domain.ports.sources.law_source import LawSource
from src.domain.shared.results import SyncReport

ENTITY = "law"


class CollectLaws:
    def __init__(
        self,
        *,
        source: LawSource,
        repository: LawRepository,
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

        laws = await self._source.fetch_all(legislature, limit=limit)
        await self._save_all(laws, run_id, report)

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report

    async def execute_one(self, uid: str, legislature: int) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        run_id = await self._log.start_run(ENTITY)
        law = await self._source.fetch_by_uid(uid, legislature)
        if law is None:
            logger.warning("collect.not_found entity={} uid={}", ENTITY, uid)
        else:
            await self._save_all([law], run_id, report)
        report.finish()
        await self._log.finish_run(run_id, report)
        return report

    async def _save_all(self, laws, run_id: int, report: SyncReport) -> None:
        s3_key = getattr(self._source, "last_s3_key", None)
        for law in laws:
            report.processed += 1
            if self._dry_run:
                report.skipped += 1
                continue
            try:
                outcome = await self._repository.save(law, run_id=run_id, s3_key=s3_key)
            except Exception:
                report.record_failure(law.dossier_uid)
                logger.exception("collect.item_failed entity={} uid={}", ENTITY, law.dossier_uid)
                continue
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)
