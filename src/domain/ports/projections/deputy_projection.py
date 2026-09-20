"""
Port: project deputies from `raw` into the display schema (`public`).

A projection never touches the network. It reads facts already collected and
adapts them to a schema we do not own: integer ids, mandatory slugs, English
enums. When a mapping is wrong, re-running the projection is enough.
"""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class DeputyProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        Groups, then deputies, then mandates — in that order, because
        deputy_mandate.political_group_id is NOT NULL in the display schema.
        Idempotent: re-running updates, never duplicates.
        """
        ...
