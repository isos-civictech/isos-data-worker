"""Port: write sittings into the `raw` schema."""

from abc import ABC, abstractmethod

from src.domain.entities.debate import Debate
from src.domain.shared.results import SaveOutcome


class DebateRepository(ABC):
    @abstractmethod
    async def save(
        self,
        debate: Debate,
        *,
        run_id: int,
        s3_key: str | None = None,
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a sitting, its points and its speeches."""
        ...
