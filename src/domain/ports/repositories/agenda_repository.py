"""Port: write scheduled sittings into the `raw` schema."""

from abc import ABC, abstractmethod

from src.domain.entities.agenda_item import AgendaItem
from src.domain.shared.results import SaveOutcome


class AgendaRepository(ABC):
    @abstractmethod
    async def save(
        self, item: AgendaItem, *, run_id: int, s3_key: str | None = None
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a sitting and its agenda points."""
        ...
