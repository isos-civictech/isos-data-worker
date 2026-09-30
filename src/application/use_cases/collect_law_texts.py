"""
Scrape the articles of every law text not fetched yet. One HTTP request per
text (~400 KB), so the run is incremental by design: a text uid never changes.
"""

from loguru import logger

from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.repositories.law_text_repository import LawTextRepository
from src.domain.ports.sources.law_text_source import LawTextSource
from src.domain.shared.results import SyncReport

ENTITY = "law_text"


class CollectLawTexts:
    def __init__(
        self,
        *,
        source: LawTextSource,
        repository: LawTextRepository,
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
        texte_uid: str | None = None,
        limit: int | None = None,
    ) -> SyncReport:
        report = SyncReport(entity=ENTITY)
        run_id = await self._log.start_run(ENTITY)
        if texte_uid:
            uids = [texte_uid]
        else:
            uids = await self._repository.pending_texte_uids(legislature, dossier_uid=dossier_uid)
        uids = uids[:limit] if limit else uids
        logger.info(
            "collect.start entity={} legislature={} pending={} dossier={} dry_run={}",
            ENTITY,
            legislature,
            len(uids),
            dossier_uid,
            self._dry_run,
        )

        for uid in uids:
            report.processed += 1
            if self._dry_run:
                report.skipped += 1
                continue
            try:
                law_text = await self._source.fetch(uid, legislature)
                if law_text is None:
                    await self._repository.mark_unavailable(uid, run_id=run_id)
                    report.skipped += 1
                    continue
                outcome = await self._repository.save(
                    law_text, run_id=run_id, s3_key=getattr(self._source, "last_s3_key", None)
                )
            except Exception:
                report.record_failure(uid)
                logger.exception("collect.item_failed entity={} uid={}", ENTITY, uid)
                continue
            report.created += int(outcome.created)
            report.updated += int(not outcome.created)

        report.finish()
        await self._log.finish_run(run_id, report)
        logger.info("collect.done {}", report.as_dict())
        return report
