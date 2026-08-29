import httpx
import pytest
import respx

from src.infrastructure.http.client import HttpClient, RetryableStatus

URL = "https://data.assemblee-nationale.fr/test.xml"


@respx.mock
async def test_transient_500_is_retried_then_succeeds():
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, content=b"<acteur/>"),
        ]
    )

    async with HttpClient(timeout_s=5, max_attempts=3) as client:
        assert await client.get_bytes(URL) == b"<acteur/>"

    assert route.call_count == 2


@respx.mock
async def test_404_is_not_retried():
    """Retrying a 404 wastes 30 seconds per missing record and cannot succeed."""
    route = respx.get(URL).mock(return_value=httpx.Response(404))

    async with HttpClient(timeout_s=5, max_attempts=3) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_bytes(URL)

    assert route.call_count == 1


@respx.mock
async def test_429_is_retried():
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"ok": True})]
    )

    async with HttpClient(timeout_s=5, max_attempts=3) as client:
        assert await client.get_json(URL) == {"ok": True}

    assert route.call_count == 2


@respx.mock
async def test_gives_up_after_max_attempts():
    route = respx.get(URL).mock(return_value=httpx.Response(503))

    async with HttpClient(timeout_s=5, max_attempts=3) as client:
        with pytest.raises(RetryableStatus):
            await client.get_bytes(URL)

    assert route.call_count == 3


async def test_refuses_use_outside_context_manager():
    """The client owns a connection pool; using it unopened is a bug, not a warning."""
    with pytest.raises(RuntimeError):
        await HttpClient().get_bytes(URL)
