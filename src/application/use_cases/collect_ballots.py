"""Collect public votes (scrutins) from the Assemblée nationale into `raw`."""

from datetime import date

from loguru import logger

from src.application.use_cases._collect import CollectUseCase
from src.domain.shared.results import SyncReport

ENTITY = "ballot"


class CollectBallots(CollectUseCase):
    entity = ENTITY

    async def execute(
        self,
        legislature: int,
        *,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
        agenda_uids: set[str] | None = None,
    ) -> SyncReport:
        """`agenda_uids`: keep only the scrutins of these sittings (a scoped sync)."""
        report, run_id = await self._begin(legislature)
        logger.info(
            "collect.start entity={} legislature={} since={} until={} limit={} dry_run={}",
            ENTITY,
            legislature,
            since,
            until,
            limit,
            self._dry_run,
        )
        ballots = await self._source.fetch_all(legislature, since=since, until=until, limit=limit)
        if agenda_uids is not None:
            ballots = [b for b in ballots if b.agenda_uid in agenda_uids]
        for ballot in ballots:
            await self._save_ballot(report, run_id, ballot)
        return await self._end(report, run_id)

    async def _save_ballot(self, report: SyncReport, run_id: int, ballot) -> None:
        await self._save_item(
            report,
            ballot.uid,
            lambda: self._repository.save(ballot, run_id=run_id, s3_key=self._s3_key),
        )

    async def _save_one(self, report, run_id, item, legislature) -> None:
        await self._save_ballot(report, run_id, item)
