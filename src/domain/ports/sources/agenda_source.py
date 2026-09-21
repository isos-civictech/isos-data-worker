"""Port: read the sittings agenda (past, current and upcoming) from the Assemblée nationale."""

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.agenda_item import AgendaItem
from src.domain.shared.validators import Legislature


class AgendaSource(ABC):
    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[AgendaItem]:
        """Assemblée public sittings only, optionally within [since, until] on start_at."""
        ...

    @abstractmethod
    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> AgendaItem | None: ...
