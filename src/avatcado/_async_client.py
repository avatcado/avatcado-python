from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from avatcado._async_resources.async_vat import AsyncVatAsyncResource
from avatcado._async_resources.eori import AsyncEoriResource
from avatcado._async_resources.rates import AsyncRatesResource
from avatcado._async_resources.vat import AsyncVatResource
from avatcado._config import AvatcadoConfig


class AsyncAvatcado:
    """Asynchronous client for the Avatcado VAT validation API."""

    vat: AsyncVatResource
    rates: AsyncRatesResource
    eori: AsyncEoriResource
    async_vat: AsyncVatAsyncResource

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_retry_delay: Optional[float] = None,
    ) -> None:
        """Create a client.

        ``timeout`` is in seconds and applies to each attempt (default 30).

        ``max_retries`` is the number of extra attempts after a retryable failure. The default
        is 0: the SDK does not retry. When set, a burst-limit 429 and a 503 are retried on
        every method; a timeout, a network error, a 502 and a 504 are retried on GET requests
        only (``vat.validate``, ``rates.*``, ``eori.validate``), because a POST may already
        have been accepted. The SDK waits for ``Retry-After`` when the API sends it, otherwise
        0.5 s doubling up to 8 s.

        ``max_retry_delay`` is the longest wait before one retry, in seconds (default 60). An
        error whose ``Retry-After`` is longer (the monthly quota, a register outage) is raised
        at once.
        """
        self._config = AvatcadoConfig.resolve(
            api_key, base_url, timeout, max_retries, max_retry_delay
        )
        self._http = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self.vat = AsyncVatResource(self._http, self._config)
        self.rates = AsyncRatesResource(self._http, self._config)
        self.eori = AsyncEoriResource(self._http, self._config)
        self.async_vat = AsyncVatAsyncResource(self._http, self._config)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncAvatcado:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()
