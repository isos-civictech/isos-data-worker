"""Port: read deputies and political groups from the Assemblée nationale."""
from abc import ABC, abstractmethod

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.shared.validators import Legislature


class DeputySource(ABC):
    @abstractmethod
    async def fetch_political_groups(
        self,
        legislature: Legislature,
    ) -> list[PoliticalGroupRef]:
        """Must be called before fetch_all: mandates reference groups by uid."""
        ...

    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
    ) -> list[Deputy]:
        """All deputies with their mandates. `limit` is for development."""
        ...

    @abstractmethod
    async def fetch_by_uid(
        self,
        uid: str,
        legislature: Legislature,
    ) -> Deputy | None:
        """One deputy by AN uid ("PA1592"), or None."""
        ...
