from __future__ import annotations

from typing import Dict, Optional

import httpx

from avatcado._base_client import build_headers, handle_response, parse_rate_limit
from avatcado._config import AvatcadoConfig
from avatcado._errors import AvatcadoError, ValidationError
from avatcado._types import (
    EoriResponseMeta,
    EoriValidateResponse,
    EoriValidationResult,
    _require_key,
)


class AsyncEoriResource:
    def __init__(self, http: httpx.AsyncClient, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    async def validate(
        self,
        eori_number: str,
        *,
        cache: bool = True,
        request_id: Optional[str] = None,
    ) -> EoriValidateResponse:
        """Check one EORI number against the register that issued it.

        GB numbers are checked with HMRC; numbers from the 27 EU member states and XI with
        the European Commission's EORI validation service. Pass ``cache=False`` to skip the
        cache and ask the register again.
        """
        if not eori_number or not eori_number.strip():
            raise ValidationError(
                "eori_number is required",
                code="missing_parameter",
                status_code=400,
            )

        params: Dict[str, str] = {"eori_number": eori_number.strip()}
        if cache is False:
            params["cache"] = "false"

        try:
            response = await self._http.get(
                "/v1/eori/validate",
                params=params,
                headers=build_headers(self._config.api_key, request_id),
            )
        except httpx.TimeoutException:
            raise AvatcadoError(
                f"Request timed out after {self._config.timeout}s",
                code="timeout",
                status_code=0,
            )
        except httpx.HTTPError as exc:
            raise AvatcadoError(str(exc), code="network_error", status_code=0)

        body = handle_response(response)
        context = "EoriValidateResponse"
        return EoriValidateResponse(
            data=EoriValidationResult.from_dict(_require_key(body, "data", context)),
            meta=EoriResponseMeta.from_dict(_require_key(body, "meta", context)),
            rate_limit=parse_rate_limit(response.headers),
        )
