"""
Storage adapter used when no S3 is configured.

There is no object storage in the cluster today, and none in the local compose
file either. Rather than scattering `if settings.s3_enabled` across the use
cases, the composition root injects this adapter and everything downstream runs
unchanged. Only the raw-file archive is lost, and nothing reads it back during
normal operation.
"""
from loguru import logger

from src.domain.ports.storage import RawStoragePort


class NoopStorage(RawStoragePort):
    async def put(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        logger.debug("storage.skipped key={} bytes={}", key, len(body))
        return key

    async def exists(self, key: str) -> bool:
        return False
