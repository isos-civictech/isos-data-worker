"""
Our S3 copy comes first: the Assemblée's archives are large (up to 340 MB)
and its site is not always up. A download only happens when the key is
missing, or when a refresh is explicitly asked for (`refresh=True`).
"""

from loguru import logger

from src.domain.ports.storage import RawStoragePort
from src.infrastructure.http.client import HttpClient


async def load_archive(
    http: HttpClient,
    storage: RawStoragePort,
    *,
    url: str,
    key: str,
    content_type: str = "application/zip",
    refresh: bool = False,
    strict: bool = False,
) -> bytes:
    """S3 first. With `refresh`, a failed download falls back to the stored copy unless `strict`."""
    if not refresh:
        cached = await storage.get(key)
        if cached is not None:
            logger.info("archive.from_s3 key={} bytes={}", key, len(cached))
            return cached
    try:
        payload = await http.get_bytes(url)
    except Exception:
        stale = None if strict else await storage.get(key)
        if stale is None:
            raise
        logger.warning(
            "archive.refresh_failed_using_s3 url={} key={} bytes={}", url, key, len(stale)
        )
        return stale
    await storage.put(key, payload, content_type=content_type)
    logger.info("archive.downloaded url={} key={} bytes={}", url, key, len(payload))
    return payload
