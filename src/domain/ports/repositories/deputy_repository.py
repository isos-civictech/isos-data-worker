"""
Port: write deputies into the `raw` schema.
"""
from abc import ABC, abstractmethod

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.shared.results import SaveOutcome


class DeputyRepository(ABC):
    @abstractmethod
    async def save(
        self,
        deputy: Deputy,
        *,
        legislature: int,
        run_id: int,
        source_url: str | None = None,
        checksum: str | None = None,
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a deputy, its mandates and its audit line."""
        ...

    @abstractmethod
    async def save_political_groups(self, groups: list[PoliticalGroupRef]) -> int:
        """Upsert groups; must run before any deputy."""
        ...
