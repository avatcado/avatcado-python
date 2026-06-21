from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from avatcado._base_client import build_headers, handle_response, parse_rate_limit
from avatcado._config import AvatcadoConfig
from avatcado._errors import AvatcadoError, ValidationError
from avatcado._types import (
    AsyncBatchData,
    AsyncBatchValidateResponse,
    AsyncMeta,
    AsyncValidateData,
    AsyncValidateResponse,
)


class VatAsyncResource:
    def __init__(self, http: httpx.Client, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    def validate(
        self,
        vat_number: str,
        *,
        requester_vat_number: Optional[str] = None,
        cache: bool = True,
        request_id: Optional[str] = None,
    ) -> AsyncValidateResponse:
        if not vat_number or not vat_number.strip():
            raise ValidationError(
                "vat_number is required",
                code="missing_parameter",
                status_code=400,
            )

        body: Dict[str, Any] = {"vat_number": vat_number.strip()}
        if requester_vat_number is not None:
            body["requester_vat_number"] = requester_vat_number
        if cache is False:
            body["cache"] = False

        try:
            response = self._http.post(
                "/v1/validate/async",
                json=body,
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

        data = handle_response(response)
        return AsyncValidateResponse(
            data=AsyncValidateData.from_dict(data["data"]),
            meta=AsyncMeta.from_dict(data["meta"]),
            rate_limit=parse_rate_limit(response.headers),
        )

    def validate_batch(
        self,
        vat_numbers: List[str],
        *,
        requester_vat_number: Optional[str] = None,
        cache: bool = True,
        request_id: Optional[str] = None,
    ) -> AsyncBatchValidateResponse:
        if not vat_numbers:
            raise ValidationError(
                "At least one VAT number is required",
                code="missing_parameter",
                status_code=400,
            )

        body: Dict[str, Any] = {"vat_numbers": [v.strip() for v in vat_numbers]}
        if requester_vat_number is not None:
            body["requester_vat_number"] = requester_vat_number
        if cache is False:
            body["cache"] = False

        try:
            response = self._http.post(
                "/v1/validate/async/batch",
                json=body,
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

        data = handle_response(response)
        return AsyncBatchValidateResponse(
            data=AsyncBatchData.from_dict(data["data"]),
            meta=AsyncMeta.from_dict(data["meta"]),
            rate_limit=parse_rate_limit(response.headers),
        )
