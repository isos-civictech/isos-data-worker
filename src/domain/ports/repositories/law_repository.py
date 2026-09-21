"""Port: write legislative dossiers into the `raw` schema."""

from abc import ABC, abstractmethod

from src.domain.entities.law import Law
from src.domain.shared.results import SaveOutcome


class LawRepository(ABC):
    @abstractmethod
    async def save(self, law: Law, *, run_id: int, s3_key: str | None = None) -> SaveOutcome:
        """Atomic, idempotent upsert of a dossier and its stages."""
        ...
