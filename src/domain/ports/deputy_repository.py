# src/domain/ports/deputy_repository.py
from abc import ABC, abstractmethod
from src.domain.entities.deputy import Deputy
from src.domain.shared.validators import Legislature


class DeputyRepository(ABC):

    @abstractmethod
    async def fetch_all(self, legislature: Legislature) -> list[Deputy]:
        """
        Fetch all deputies for the current legislature.
        """
        ...

    @abstractmethod
    async def fetch_by_uid(
        self,
        uid: str,
        legislature: Legislature
    ) -> Deputy | None:
        """
        Fetch a single deputy by their AN uid (e.g. "PA1234").
        """
        ...
        
    @abstractmethod
    async def fetch_career(self, uid: str) -> Deputy | None:
        """
        Fetch a deputy with ALL their mandates across all legislatures.
        Returns None if uid unknown.
        """
        ...