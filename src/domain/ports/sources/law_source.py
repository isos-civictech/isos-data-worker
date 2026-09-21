"""Port: read legislative dossiers from the Assemblée nationale."""

from abc import ABC, abstractmethod

from src.domain.entities.law import Law
from src.domain.shared.validators import Legislature


class LawSource(ABC):
    @abstractmethod
    async def fetch_all(self, legislature: Legislature, limit: int | None = None) -> list[Law]:
        """Every dossier in the legislature's archive, including older ones still in navette."""
        ...

    @abstractmethod
    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Law | None: ...
