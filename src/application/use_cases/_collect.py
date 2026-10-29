"""Skeleton shared by every `collect_*` use case: run bookkeeping and per-item saving."""

from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from src.domain.shared.results import SaveOutcome, SyncReport


class CollectUseCase:
    """Subclasses set `entity` and keep only what is specific to their source."""

    entity: str

    def __init__(
        self, *, source: Any, repository: Any, log_repository: Any, dry_run: bool = False
    ) -> None:
        self._source = source
        self._repository = repository
        self._log = log_repository
        self._dry_run = dry_run

    @property
    def _s3_key(self) -> str | None:
        return getattr(self._source, "last_s3_key", None)

    async def _begin(self, legislature: int | None = None) -> tuple[SyncReport, int]:
        """Open a run; `legislature` also records the archive URL it reads from."""
        archive_url = getattr(self._source, "archive_url", None)
        source_url = archive_url(legislature) if archive_url and legislature is not None else None
        run_id = await self._log.start_run(self.entity, source_url=source_url)
        return SyncReport(entity=self.entity), run_id

    async def _end(self, report: SyncReport, run_id: int, *, log: bool = True) -> SyncReport:
        report.finish()
        await self._log.finish_run(run_id, report)
        if log:
            logger.info("collect.done {}", report.as_dict())
        return report

    async def _save_item(
        self,
        report: SyncReport,
        uid: str,
        save: Callable[[], Awaitable[SaveOutcome | None]],
    ) -> None:
        """Count one item; a failing save is logged and does not stop the run.

        `save` returns None when the item was intentionally left out (counted as skipped).
        """
        report.processed += 1
        if self._dry_run:
            report.skipped += 1
            return
        try:
            outcome = await save()
        except Exception:
            report.record_failure(uid)
            logger.exception("collect.item_failed entity={} uid={}", self.entity, uid)
            return
        if outcome is None:
            report.skipped += 1
            return
        report.created += int(outcome.created)
        report.updated += int(not outcome.created)

    async def execute_one(self, uid: str, legislature: int) -> SyncReport:
        """Replay a single record — what POST /collect/{dataset}?uid= calls."""
        report, run_id = await self._begin()
        item = await self._source.fetch_by_uid(uid, legislature)
        if item is None:
            logger.warning("collect.not_found entity={} uid={}", self.entity, uid)
        else:
            await self._save_one(report, run_id, item, legislature)
        return await self._end(report, run_id, log=False)

    async def _save_one(self, report: SyncReport, run_id: int, item: Any, legislature: int) -> None:
        raise NotImplementedError
