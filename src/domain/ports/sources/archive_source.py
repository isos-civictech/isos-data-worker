"""Port: a source backed by one Assemblée archive per legislature, mirrored in S3."""

from abc import ABC, abstractmethod


class ArchiveSource(ABC):
    @abstractmethod
    def archive_url(self, legislature: int) -> str: ...

    @abstractmethod
    def archive_key(self, legislature: int) -> str:
        """Where the archive lives in our S3."""
        ...

    @abstractmethod
    async def refresh_archive(self, legislature: int) -> str:
        """Download the archive again and overwrite the S3 copy; returns the key."""
        ...
