"""
Port: project deputies from `raw` into the display schema (`public`).
"""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class DeputyProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        Groups, then deputies, then mandates — in that order
        """
        ...
