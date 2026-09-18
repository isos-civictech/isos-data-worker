"""Port: one row per run in raw.ingestion_run."""
from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class IngestionLogRepository(ABC):
    @abstractmethod
    async def start_run(
        self, entity_type: str, source_url: str | None = None, s3_key: str | None = None
    ) -> int:
        """Open an execution and return its id."""
        ...

    @abstractmethod
    async def finish_run(self, run_id: int, report: SyncReport) -> None:
        """Close the execution with its counters. Always called, even on failure."""
        ...
