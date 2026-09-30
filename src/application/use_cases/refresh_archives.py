"""Re-download the Assemblée archives into S3, without touching the database."""

from loguru import logger

from src.domain.ports.sources.archive_source import ArchiveSource


class RefreshArchives:
    def __init__(self, sources: dict[str, ArchiveSource]) -> None:
        self._sources = sources

    @property
    def datasets(self) -> list[str]:
        return list(self._sources)

    async def execute(self, legislature: int, datasets: list[str] | None = None) -> dict[str, str]:
        """dataset -> S3 key, for the datasets asked (all by default)."""
        keys = {}
        for name in datasets or self.datasets:
            source = self._sources[name]
            logger.info("refresh.start dataset={} url={}", name, source.archive_url(legislature))
            keys[name] = await source.refresh_archive(legislature)
            logger.info("refresh.done dataset={} key={}", name, keys[name])
        return keys
