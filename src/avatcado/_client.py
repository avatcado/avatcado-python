from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from avatcado._config import AvatcadoConfig
from avatcado._resources.async_vat import VatAsyncResource
from avatcado._resources.eori import EoriResource
from avatcado._resources.rates import RatesResource
from avatcado._resources.vat import VatResource


class Avatcado:
    """Synchronous client for the Avatcado VAT validation API."""

    vat: VatResource
    rates: RatesResource
    eori: EoriResource
    async_vat: VatAsyncResource

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
        self._http = httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self.vat = VatResource(self._http, self._config)
        self.rates = RatesResource(self._http, self._config)
        self.eori = EoriResource(self._http, self._config)
        self.async_vat = VatAsyncResource(self._http, self._config)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Avatcado:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()
