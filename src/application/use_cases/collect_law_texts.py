"""
Scrape the articles of every law text not fetched yet. One HTTP request per
text (~400 KB), so the run is incremental by design: a text uid never changes.
"""

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "law_text"


class CollectLawTexts(CollectUseCase):
    entity = ENTITY

    async def execute(
        self,
        legislature: int,
        *,
        dossier_uid: str | None = None,
        texte_uid: str | None = None,
        limit: int | None = None,
    ) -> SyncReport:
        report, run_id = await self._begin()
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
            await self._save_item(
                report, uid, lambda uid=uid: self._fetch_and_save(uid, legislature, run_id)
            )
        return await self._end(report, run_id)

    async def _fetch_and_save(self, uid: str, legislature: int, run_id: int):
        law_text = await self._source.fetch(uid, legislature)
        if law_text is None:
            await self._repository.mark_unavailable(uid, run_id=run_id)
            return None
        return await self._repository.save(law_text, run_id=run_id, s3_key=self._s3_key)
