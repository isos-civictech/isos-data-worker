import pytest

from src.infrastructure.adapters.archive_cache import load_archive
from tests.adapters.test_an_deputy_adapter import InMemoryStorage


class FakeHttp:
    def __init__(self, body: bytes):
        self.body = body
        self.calls = 0

    async def get_bytes(self, url):
        self.calls += 1
        return self.body


async def test_s3_copy_is_used_when_present():
    storage, http = InMemoryStorage(), FakeHttp(b"fresh")
    storage.objects["raw/x.zip"] = b"cached"

    assert await load_archive(http, storage, url="u", key="raw/x.zip") == b"cached"
    assert http.calls == 0, "no download when the archive is already in S3"


async def test_download_fills_s3_when_missing():
    storage, http = InMemoryStorage(), FakeHttp(b"fresh")

    assert await load_archive(http, storage, url="u", key="raw/x.zip") == b"fresh"
    assert storage.objects["raw/x.zip"] == b"fresh" and http.calls == 1


async def test_refresh_downloads_even_when_present():
    storage, http = InMemoryStorage(), FakeHttp(b"fresh")
    storage.objects["raw/x.zip"] = b"stale"

    assert await load_archive(http, storage, url="u", key="raw/x.zip", refresh=True) == b"fresh"
    assert storage.objects["raw/x.zip"] == b"fresh"


class BrokenHttp:
    async def get_bytes(self, url):
        raise ConnectionError("peer closed connection")


async def test_failed_refresh_falls_back_to_s3_copy():
    storage = InMemoryStorage()
    storage.objects["raw/x.zip"] = b"stale"

    assert (
        await load_archive(BrokenHttp(), storage, url="u", key="raw/x.zip", refresh=True)
        == b"stale"
    )


async def test_strict_refresh_does_not_hide_the_failure():
    storage = InMemoryStorage()
    storage.objects["raw/x.zip"] = b"stale"

    with pytest.raises(ConnectionError):
        await load_archive(
            BrokenHttp(), storage, url="u", key="raw/x.zip", refresh=True, strict=True
        )


async def test_failed_download_without_s3_copy_raises():
    with pytest.raises(ConnectionError):
        await load_archive(BrokenHttp(), InMemoryStorage(), url="u", key="raw/x.zip")
