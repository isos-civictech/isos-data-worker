"""Port: project amendments from `raw` into `public.amendment`."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class AmendmentProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """Only amendments whose law exists in public.law are projected."""
        ...
