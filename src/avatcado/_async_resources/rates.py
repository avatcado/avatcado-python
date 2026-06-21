from __future__ import annotations

from urllib.parse import quote

import httpx

from avatcado._base_client import build_headers, handle_response, parse_rate_limit
from avatcado._config import AvatcadoConfig
from avatcado._errors import AvatcadoError
from avatcado._types import (
    GetRateResponse,
    ListRatesResponse,
    ResponseMeta,
    VatRate,
)


class AsyncRatesResource:
    def __init__(self, http: httpx.AsyncClient, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    async def list(self) -> ListRatesResponse:
        try:
            response = await self._http.get(
                "/v1/rates",
                headers=build_headers(self._config.api_key),
            )
        except httpx.TimeoutException:
            raise AvatcadoError(
                f"Request timed out after {self._config.timeout}s",
                code="timeout",
                status_code=0,
            )
        except httpx.HTTPError as exc:
            raise AvatcadoError(str(exc), code="network_error", status_code=0)

        data = handle_response(response)
        return ListRatesResponse(
            data=[VatRate.from_dict(r) for r in data["data"]],
            meta=ResponseMeta.from_dict(data["meta"]),
            rate_limit=parse_rate_limit(response.headers),
        )

    async def get(self, country_code: str) -> GetRateResponse:
        try:
            response = await self._http.get(
                f"/v1/rates/{quote(country_code, safe='')}",
                headers=build_headers(self._config.api_key),
            )
        except httpx.TimeoutException:
            raise AvatcadoError(
                f"Request timed out after {self._config.timeout}s",
                code="timeout",
                status_code=0,
            )
        except httpx.HTTPError as exc:
            raise AvatcadoError(str(exc), code="network_error", status_code=0)

        data = handle_response(response)
        return GetRateResponse(
            data=VatRate.from_dict(data["data"]),
            meta=ResponseMeta.from_dict(data["meta"]),
            rate_limit=parse_rate_limit(response.headers),
        )
