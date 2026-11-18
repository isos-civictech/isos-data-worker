"""Keep `raw` small: drop projected rows older than the retention window."""

from datetime import UTC, datetime, timedelta

from loguru import logger

from src.domain.ports.repositories.raw_purge import RawPurge


class PurgeRaw:
    def __init__(self, *, repository: RawPurge, retention_days: int) -> None:
        self._repository = repository
        self._retention_days = retention_days

    async def execute(self, *, dry_run: bool = False, days: int | None = None) -> dict[str, int]:
        """Counts by table. A retention of 0 days or less disables the purge."""
        retention = self._retention_days if days is None else days
        if retention <= 0:
            return {}
        before = (datetime.now(tz=UTC) - timedelta(days=retention)).date()
        counts = await self._repository.purge(before, dry_run=dry_run)
        logger.info("purge.raw before={} dry_run={} counts={}", before, dry_run, counts)
        return counts
