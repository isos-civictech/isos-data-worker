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
        s3_key: str | None = None,
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a deputy and its mandates.

        `updated_at` only moves when the content actually changed."""
        ...

    @abstractmethod
    async def save_political_groups(
        self, groups: list[PoliticalGroupRef], *, run_id: int, s3_key: str | None = None
    ) -> int:
        """Upsert groups; must run before any deputy."""
        ...
