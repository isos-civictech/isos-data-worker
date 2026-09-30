"""Port: read sittings (comptes rendus de séance) from the Assemblée nationale."""

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.debate import Debate
from src.domain.shared.validators import Legislature


class DebateSource(ABC):
    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Debate]:
        """
        Sittings with their points and speeches, optionally within [since, until].

        The AN publishes one archive per legislature: the range is a filter
        applied after download, not a smaller download.
        """
        ...

    @abstractmethod
    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Debate | None:
        """One sitting by AN uid ("CRSANR5L17S2025O1N037"), or None."""
        ...
