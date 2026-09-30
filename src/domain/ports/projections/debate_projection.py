"""Port: project sittings from `raw` into the display schema (`public.debate`)."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class DebateProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """One public.debate per sitting. debate_law waits for laws to be collected."""
        ...
