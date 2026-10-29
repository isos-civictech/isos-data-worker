"""Collect the sittings agenda from the Assemblée nationale into `raw`."""

from datetime import UTC, date, datetime

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "agenda"


class CollectAgenda(CollectUseCase):
    entity = ENTITY

    async def execute(
        self,
        legislature: int,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
        last: int | None = None,
    ) -> SyncReport:
        """`last`: keep only the N most recent sittings already started (a scoped sync)."""
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

        items = await self._source.fetch_all(legislature, limit=limit, since=since, until=until)
        if last is not None:
            now = datetime.now(tz=UTC)
            items = [i for i in items if i.start_at <= now][-last:]

        for item in items:
            await self._save_item(
                report,
                item.uid,
                lambda item=item: self._repository.save(item, run_id=run_id, s3_key=self._s3_key),
            )
        return await self._end(report, run_id)
