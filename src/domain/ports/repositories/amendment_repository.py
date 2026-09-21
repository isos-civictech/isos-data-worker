"""Port: write amendments into the `raw` schema."""

from abc import ABC, abstractmethod

from src.domain.entities.amendment import Amendment
from src.domain.shared.results import BatchOutcome


class AmendmentRepository(ABC):
    @abstractmethod
    async def save_batch(
        self, amendments: list[Amendment], *, run_id: int, s3_key: str | None = None
    ) -> BatchOutcome:
        """One transaction per batch: 125 000 single-row transactions is too slow."""
        ...
