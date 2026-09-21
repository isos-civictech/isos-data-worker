"""Port: write scheduled sittings into the `raw` schema."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.agenda_item import AgendaItem
from src.domain.shared.results import SaveOutcome


@dataclass(frozen=True)
class SittingLink:
    """What a sitting points at: its compte rendu and the dossiers on its agenda."""

    uid: str
    compte_rendu_uid: str | None
    dossier_uids: frozenset[str] = field(default_factory=frozenset)


class AgendaRepository(ABC):
    @abstractmethod
    async def save(
        self, item: AgendaItem, *, run_id: int, s3_key: str | None = None
    ) -> SaveOutcome:
        """Atomic, idempotent upsert of a sitting and its agenda points."""
        ...

    @abstractmethod
    async def latest_held(
        self, legislature: int, count: int, before: datetime
    ) -> list[SittingLink]:
        """The `count` most recent sittings started before `before`, newest first."""
        ...
