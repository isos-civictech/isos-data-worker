"""Port: store a raw file (S3-compatible)."""
from abc import ABC, abstractmethod


class RawStoragePort(ABC):
    @abstractmethod
    async def put(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store `body` under `key`; returns the key."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...
