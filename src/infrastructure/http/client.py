"""
HTTP client with retries.

Retry policy, and the reasoning behind it:
  - timeouts, transport errors, 5xx and 429 are retried with exponential backoff:
    they are transient, the same request may well succeed a second later;
  - 4xx is NEVER retried.
  - database writes are not retried at all.
"""
import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class RetryableStatus(Exception):
    """Raised when a request returns a status code that is retryable (5xx or 429)."""


class HttpClient:
    def __init__(self, timeout_s: float = 30.0, max_attempts: int = 3) -> None:
        self._timeout_s = timeout_s
        self._max_attempts = max_attempts
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HttpClient":
        # One client for the whole run: it holds the connection pool. Creating
        # one per request would reopen a TLS connection every time.
        self._client = httpx.AsyncClient(
            timeout=self._timeout_s,
            follow_redirects=True,
            headers={"User-Agent": "isos-data-worker (contact: isos-civictech)"},
        )
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_bytes(self, url: str) -> bytes:
        response = await self._get(url)
        return response.content

    async def get_text(self, url: str) -> str:
        response = await self._get(url)
        return response.text

    async def get_json(self, url: str):
        response = await self._get(url)
        return response.json()

    async def _get(self, url: str) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("HttpClient must be used as an async context manager")
        
        @retry(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.TransportError, RetryableStatus)
            ),
            reraise=True,
            before_sleep=lambda state: logger.warning(
                "http.retry url={} attempt={}", url, state.attempt_number
            ),
        )
        async def _attempt() -> httpx.Response:
            response = await self._client.get(url)
            if response.status_code >= 500 or response.status_code == 429:
                raise RetryableStatus(f"{response.status_code} on {url}")
            response.raise_for_status()  # 4xx: raises, and is not retried
            return response

        return await _attempt()
