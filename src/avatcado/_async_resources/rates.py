from __future__ import annotations

from typing import Optional

import httpx

from avatcado import _operations as ops
from avatcado._base_client import arequest
from avatcado._config import AvatcadoConfig
from avatcado._types import GetRateResponse, ListRatesResponse


class AsyncRatesResource:
    def __init__(self, http: httpx.AsyncClient, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    async def list(self, *, request_id: Optional[str] = None) -> ListRatesResponse:
        """VAT rates for every supported country."""
        call = ops.list_rates_call(request_id)
        return ops.parse_list_rates(await arequest(self._http, self._config, call))

    async def get(self, country_code: str, *, request_id: Optional[str] = None) -> GetRateResponse:
        """VAT rates for one country, by two-letter code."""
        call = ops.get_rate_call(country_code, request_id)
        return ops.parse_get_rate(await arequest(self._http, self._config, call))
