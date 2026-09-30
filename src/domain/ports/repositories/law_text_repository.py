"""Port: write law texts into the `raw` schema, and say which ones are still to fetch."""

from abc import ABC, abstractmethod

from src.domain.entities.law_text import LawText
from src.domain.shared.results import SaveOutcome


class LawTextRepository(ABC):
    @abstractmethod
    async def pending_texte_uids(
        self, legislature: int, *, dossier_uid: str | None = None
    ) -> list[str]:
        """Assemblée law texts known from the dossiers but not fetched yet (a uid never changes)."""
        ...

    @abstractmethod
    async def save(
        self, law_text: LawText, *, run_id: int, s3_key: str | None = None
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a text and its articles."""
        ...

    @abstractmethod
    async def mark_unavailable(self, texte_uid: str, *, run_id: int) -> None:
        """Remember a 404 so the uid is not retried on every run."""
        ...
