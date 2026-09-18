"""
Port: the ingestion audit trail.

Two kinds of logs:

    raw.ingestion_run  "when were entities last ingested, and how did it go?"
    raw.ingestion_log  "where does this entity come from, which raw file, which fingerprint?"
"""
from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class IngestionLogRepository(ABC):
    @abstractmethod
    async def start_run(self, entity_type: str, source_url: str | None = None) -> int:
        """Open an execution and return its id."""
        ...

    @abstractmethod
    async def finish_run(self, run_id: int, report: SyncReport) -> None:
        """Close the execution with its counters. Always called, even on failure."""
        ...
