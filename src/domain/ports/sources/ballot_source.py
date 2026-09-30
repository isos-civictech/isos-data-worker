"""Port: read public votes (scrutins) from the Assemblée nationale."""

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.ballot import Ballot
from src.domain.shared.validators import Legislature


class BallotSource(ABC):
    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        *,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> list[Ballot]: ...

    @abstractmethod
    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Ballot | None: ...
