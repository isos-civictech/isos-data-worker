"""Collect legislative dossiers from the Assemblée nationale into `raw`."""

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "law"


class CollectLaws(CollectUseCase):
    entity = ENTITY

    async def execute(
        self, legislature: int, limit: int | None = None, dossier_uids: set[str] | None = None
    ) -> SyncReport:
        """`dossier_uids`: keep only these dossiers (a scoped sync)."""
        report, run_id = await self._begin(legislature)
        logger.info(
            "collect.start entity={} legislature={} limit={} dry_run={}",
            ENTITY,
            legislature,
            limit,
            self._dry_run,
        )

        laws = await self._source.fetch_all(legislature, limit=limit)
        if dossier_uids is not None:
            laws = [law for law in laws if law.dossier_uid in dossier_uids]
        for law in laws:
            await self._save_law(report, run_id, law)
        return await self._end(report, run_id)

    async def _save_law(self, report: SyncReport, run_id: int, law) -> None:
        await self._save_item(
            report,
            law.dossier_uid,
            lambda: self._repository.save(law, run_id=run_id, s3_key=self._s3_key),
        )

    async def _save_one(self, report, run_id, item, legislature) -> None:
        await self._save_law(report, run_id, item)
