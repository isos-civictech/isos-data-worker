"""Port: project scheduled sittings from `raw` into `public.debate`."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class AgendaProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        One public.debate row per Assemblée sitting, keyed by the agenda uid,
        with calendar_status scheduled / completed / cancelled. The compte rendu
        projection enriches the same row once the sitting has been held.
        """
        ...
