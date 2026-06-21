from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from avatcado._config import AvatcadoConfig
from avatcado._resources.async_vat import VatAsyncResource
from avatcado._resources.rates import RatesResource
from avatcado._resources.vat import VatResource


class Avatcado:
    """Synchronous client for the Avatcado VAT validation API."""

    vat: VatResource
    rates: RatesResource
    async_vat: VatAsyncResource

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._config = AvatcadoConfig.resolve(api_key, base_url, timeout)
        self._http = httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self.vat = VatResource(self._http, self._config)
        self.rates = RatesResource(self._http, self._config)
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
