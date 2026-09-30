"""Port: project dossiers from `raw` into `public.law`, `law_reading` and `debate_law`."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class LawProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        Only dossiers that are laws (projet / proposition de loi) get a
        public.law row; résolutions, rapports and missions are skipped.
        Each reading stage becomes a law_reading, and every sitting a law
        was discussed in becomes a debate_law link.
        """
        ...
