"""
Collect sittings from the Assemblée nationale into `raw`.

Same shape as collect_deputies: ports only, one save per sitting, a failing
record is counted and logged and the run goes on.
"""

from datetime import date

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "debate"


class CollectDebates(CollectUseCase):
    entity = ENTITY

    async def execute(
        self,
        legislature: int,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
        uids: set[str] | None = None,
    ) -> SyncReport:
        """`uids`: keep only these comptes rendus (a scoped sync)."""
        report, run_id = await self._begin(legislature)
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
        if uids is not None:
            debates = [d for d in debates if d.uid in uids]

        for debate in debates:
            await self._save_debate(report, run_id, debate)
        return await self._end(report, run_id)

    async def _save_debate(self, report: SyncReport, run_id: int, debate) -> None:
        await self._save_item(
            report,
            debate.uid,
            lambda: self._repository.save(debate, run_id=run_id, s3_key=self._s3_key),
        )

    async def _save_one(self, report, run_id, item, legislature) -> None:
        await self._save_debate(report, run_id, item)
