from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from avatcado._async_resources.async_vat import AsyncVatAsyncResource
from avatcado._async_resources.rates import AsyncRatesResource
from avatcado._async_resources.vat import AsyncVatResource
from avatcado._config import AvatcadoConfig


class AsyncAvatcado:
    """Asynchronous client for the Avatcado VAT validation API."""

    vat: AsyncVatResource
    rates: AsyncRatesResource
    async_vat: AsyncVatAsyncResource

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._config = AvatcadoConfig.resolve(api_key, base_url, timeout)
        self._http = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self.vat = AsyncVatResource(self._http, self._config)
        self.rates = AsyncRatesResource(self._http, self._config)
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
