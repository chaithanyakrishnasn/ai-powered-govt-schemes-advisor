"""Shared async HTTP client with per-host rate limiting and tenacity retries."""

import asyncio
import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


class AsyncHTTPClient:
    """Async HTTP client with per-host rate limiting and tenacity retries."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str],
        rate_limit: float = 2.0,
        concurrency: int = 4,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._headers = headers
        self._timeout = timeout
        self._interval = 1.0 / rate_limit
        self._sem = asyncio.Semaphore(concurrency)
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        self._client = httpx.AsyncClient(headers=self._headers, timeout=self._timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_should_retry),
        reraise=True,
    )
    async def get(self, path: str, **params: str | int) -> dict:  # type: ignore[type-arg]
        assert self._client is not None, "Use as async context manager"
        url = f"{self._base_url}{path}"
        async with self._sem:
            async with self._lock:
                now = time.monotonic()
                wait = self._interval - (now - self._last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_request = time.monotonic()
            resp = await self._client.get(url, params=params)  # type: ignore[arg-type]
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
