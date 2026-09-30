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
) -> bytes:
    if not refresh:
        cached = await storage.get(key)
        if cached is not None:
            logger.info("archive.from_s3 key={} bytes={}", key, len(cached))
            return cached
    payload = await http.get_bytes(url)
    await storage.put(key, payload, content_type=content_type)
    logger.info("archive.downloaded url={} key={} bytes={}", url, key, len(payload))
    return payload
