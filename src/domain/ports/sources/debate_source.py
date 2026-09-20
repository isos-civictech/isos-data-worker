"""Port: read sittings (comptes rendus de séance) from the Assemblée nationale."""

from abc import ABC, abstractmethod

from src.domain.entities.debate import Debate
from src.domain.shared.validators import Legislature


class DebateSource(ABC):
    @abstractmethod
    async def fetch_all(self, legislature: Legislature, limit: int | None = None) -> list[Debate]:
        """All sittings with their points and speeches. `limit` is for development."""
        ...

    @abstractmethod
    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Debate | None:
        """One sitting by AN uid ("CRSANR5L17S2025O1N037"), or None."""
        ...
