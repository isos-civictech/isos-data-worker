"""Port: remove from `raw` what has been projected and can no longer change."""

from abc import ABC, abstractmethod
from datetime import date


class RawPurge(ABC):
    @abstractmethod
    async def purge(self, before: date, *, dry_run: bool = False) -> dict[str, int]:
        """Rows removed (or that would be, in a dry run) by table, for items older than `before`."""
        ...
