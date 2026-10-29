"""
Collect deputies from the Assemblée nationale into `raw`.

Depends on ports only. Groups are stored before deputies (mandates reference
them by uid). A failing record is counted and logged; the run goes on.
"""

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "deputy"


class CollectDeputies(CollectUseCase):
    entity = ENTITY

    async def execute(self, legislature: int, limit: int | None = None) -> SyncReport:
        report, run_id = await self._begin(legislature)

        logger.info(
            "collect.start entity={} legislature={} limit={} dry_run={}",
            ENTITY,
            legislature,
            limit,
            self._dry_run,
        )

        groups = await self._source.fetch_political_groups(legislature)
        if not self._dry_run:
            await self._repository.save_political_groups(groups, run_id=run_id, s3_key=self._s3_key)
        logger.info("collect.groups count={}", len(groups))

        deputies = await self._source.fetch_all(legislature, limit=limit)

        for deputy in deputies:
            await self._save_deputy(report, run_id, deputy, legislature, s3_key=self._s3_key)
        return await self._end(report, run_id)

    async def _save_deputy(
        self, report: SyncReport, run_id: int, deputy, legislature: int, **extra
    ) -> None:
        await self._save_item(
            report,
            deputy.uid,
            lambda: self._repository.save(deputy, legislature=legislature, run_id=run_id, **extra),
        )

    async def _save_one(self, report, run_id, item, legislature) -> None:
        # A replay does not record the archive key.
        await self._save_deputy(report, run_id, item, legislature)
