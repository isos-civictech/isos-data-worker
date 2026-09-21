"""Port: write scrutins into the `raw` schema."""

from abc import ABC, abstractmethod

from src.domain.entities.ballot import Ballot
from src.domain.shared.results import SaveOutcome


class BallotRepository(ABC):
    @abstractmethod
    async def save(self, ballot: Ballot, *, run_id: int, s3_key: str | None = None) -> SaveOutcome:
        """Atomic, idempotent upsert of a scrutin, its group lines and every deputy's vote."""
        ...
