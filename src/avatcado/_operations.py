"""Request building and response parsing shared by the sync and async resources.

Each API operation has a ``*_call`` function that validates the arguments and builds the
request, and a ``parse_*`` function that turns the 2xx response into a typed result. The
resources only choose between the blocking and the awaiting transport.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from avatcado._base_client import Call, parse, parse_rate_limit
from avatcado._errors import ValidationError
from avatcado._types import (
    AsyncBatchData,
    AsyncBatchValidateResponse,
    AsyncMeta,
    AsyncValidateData,
    AsyncValidateResponse,
    BatchResult,
    BatchResultError,
    BatchResultSuccess,
    BatchSummary,
    BatchValidateResponse,
    EoriResponseMeta,
    EoriValidateResponse,
    EoriValidationResult,
    GetRateResponse,
    ListRatesResponse,
    ResponseMeta,
    ValidateResponse,
    VatRate,
    VatValidationResult,
    _require_key,
)

MAX_BATCH_SIZE = 50


def _flags(cache: Optional[bool], fallback: Optional[bool] = None) -> Dict[str, bool]:
    """``cache`` and ``fallback`` as the API should receive them: only when the caller set one.

    Unset means the API default, which depends on the request: both default to true, and both
    default to false when ``requester_vat_number`` is supplied.
    """
    flags: Dict[str, bool] = {}
    if isinstance(cache, bool):
        flags["cache"] = cache
    if isinstance(fallback, bool):
        flags["fallback"] = fallback
    return flags


def _query_flags(cache: Optional[bool], fallback: Optional[bool] = None) -> Dict[str, str]:
    return {name: "true" if value else "false" for name, value in _flags(cache, fallback).items()}


def _require_vat_number(vat_number: str) -> str:
    if not vat_number or not vat_number.strip():
        raise ValidationError("vat_number is required", code="missing_parameter", status_code=400)
    return vat_number.strip()


def _require_vat_numbers(vat_numbers: List[str]) -> List[str]:
    if not vat_numbers:
        raise ValidationError(
            "At least one VAT number is required", code="missing_parameter", status_code=400
        )
    return [v.strip() for v in vat_numbers]


# ---- GET /v1/validate ------------------------------------------------------


def validate_call(
    vat_number: str,
    requester_vat_number: Optional[str],
    cache: Optional[bool],
    fallback: Optional[bool],
    request_id: Optional[str],
) -> Call:
    params: Dict[str, str] = {"vat_number": _require_vat_number(vat_number)}
    if requester_vat_number is not None:
        params["requester_vat_number"] = requester_vat_number
    params.update(_query_flags(cache, fallback))
    return Call("GET", "/v1/validate", params=params, request_id=request_id)


def _validate_response(body: Dict[str, Any], response: httpx.Response) -> ValidateResponse:
    context = "ValidateResponse"
    return ValidateResponse(
        data=VatValidationResult.from_dict(_require_key(body, "data", context)),
        meta=ResponseMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_validate(response: httpx.Response) -> ValidateResponse:
    return parse(response, _validate_response)


# ---- POST /v1/validate/batch -----------------------------------------------


def validate_batch_call(
    vat_numbers: List[str],
    requester_vat_number: Optional[str],
    cache: Optional[bool],
    fallback: Optional[bool],
    request_id: Optional[str],
) -> Call:
    numbers = _require_vat_numbers(vat_numbers)
    if len(numbers) > MAX_BATCH_SIZE:
        raise ValidationError(
            f"Batch size {len(numbers)} exceeds maximum of {MAX_BATCH_SIZE}",
            code="batch_too_large",
            status_code=400,
        )
    body: Dict[str, Any] = {"vat_numbers": numbers}
    if requester_vat_number is not None:
        body["requester_vat_number"] = requester_vat_number
    body.update(_flags(cache, fallback))
    return Call("POST", "/v1/validate/batch", json=body, request_id=request_id)


def _batch_response(body: Dict[str, Any], response: httpx.Response) -> BatchValidateResponse:
    context = "BatchValidateResponse"
    data = _require_key(body, "data", context)
    results: List[BatchResult] = []
    for item in _require_key(data, "results", context):
        if "data" in item:
            results.append(BatchResultSuccess.from_dict(item))
        else:
            results.append(BatchResultError.from_dict(item))
    return BatchValidateResponse(
        results=results,
        summary=BatchSummary.from_dict(_require_key(data, "summary", context)),
        meta=ResponseMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_validate_batch(response: httpx.Response) -> BatchValidateResponse:
    return parse(response, _batch_response)


# ---- POST /v1/validate/async -----------------------------------------------


def async_validate_call(
    vat_number: str,
    requester_vat_number: Optional[str],
    cache: Optional[bool],
    fallback: Optional[bool],
    request_id: Optional[str],
) -> Call:
    body: Dict[str, Any] = {"vat_number": _require_vat_number(vat_number)}
    if requester_vat_number is not None:
        body["requester_vat_number"] = requester_vat_number
    body.update(_flags(cache, fallback))
    return Call("POST", "/v1/validate/async", json=body, request_id=request_id)


def _async_validate_response(
    body: Dict[str, Any], response: httpx.Response
) -> AsyncValidateResponse:
    context = "AsyncValidateResponse"
    return AsyncValidateResponse(
        data=AsyncValidateData.from_dict(_require_key(body, "data", context)),
        meta=AsyncMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_async_validate(response: httpx.Response) -> AsyncValidateResponse:
    return parse(response, _async_validate_response)


# ---- POST /v1/validate/async/batch -----------------------------------------


def async_validate_batch_call(
    vat_numbers: List[str],
    requester_vat_number: Optional[str],
    cache: Optional[bool],
    fallback: Optional[bool],
    request_id: Optional[str],
) -> Call:
    body: Dict[str, Any] = {"vat_numbers": _require_vat_numbers(vat_numbers)}
    if requester_vat_number is not None:
        body["requester_vat_number"] = requester_vat_number
    body.update(_flags(cache, fallback))
    return Call("POST", "/v1/validate/async/batch", json=body, request_id=request_id)


def _async_batch_response(
    body: Dict[str, Any], response: httpx.Response
) -> AsyncBatchValidateResponse:
    context = "AsyncBatchValidateResponse"
    return AsyncBatchValidateResponse(
        data=AsyncBatchData.from_dict(_require_key(body, "data", context)),
        meta=AsyncMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_async_validate_batch(response: httpx.Response) -> AsyncBatchValidateResponse:
    return parse(response, _async_batch_response)


# ---- GET /v1/rates ---------------------------------------------------------


def list_rates_call(request_id: Optional[str]) -> Call:
    return Call("GET", "/v1/rates", request_id=request_id)


def _list_rates_response(body: Dict[str, Any], response: httpx.Response) -> ListRatesResponse:
    context = "ListRatesResponse"
    rates = _require_key(body, "data", context)
    if not isinstance(rates, list):
        raise TypeError("data is not a list")
    return ListRatesResponse(
        data=[VatRate.from_dict(rate) for rate in rates],
        meta=ResponseMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_list_rates(response: httpx.Response) -> ListRatesResponse:
    return parse(response, _list_rates_response)


def get_rate_call(country_code: str, request_id: Optional[str]) -> Call:
    return Call("GET", f"/v1/rates/{quote(country_code, safe='')}", request_id=request_id)


def _get_rate_response(body: Dict[str, Any], response: httpx.Response) -> GetRateResponse:
    context = "GetRateResponse"
    return GetRateResponse(
        data=VatRate.from_dict(_require_key(body, "data", context)),
        meta=ResponseMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_get_rate(response: httpx.Response) -> GetRateResponse:
    return parse(response, _get_rate_response)


# ---- GET /v1/eori/validate -------------------------------------------------


def eori_validate_call(eori_number: str, cache: Optional[bool], request_id: Optional[str]) -> Call:
    if not eori_number or not eori_number.strip():
        raise ValidationError("eori_number is required", code="missing_parameter", status_code=400)
    params: Dict[str, str] = {"eori_number": eori_number.strip()}
    params.update(_query_flags(cache))
    return Call("GET", "/v1/eori/validate", params=params, request_id=request_id)


def _eori_response(body: Dict[str, Any], response: httpx.Response) -> EoriValidateResponse:
    context = "EoriValidateResponse"
    return EoriValidateResponse(
        data=EoriValidationResult.from_dict(_require_key(body, "data", context)),
        meta=EoriResponseMeta.from_dict(_require_key(body, "meta", context)),
        rate_limit=parse_rate_limit(response.headers),
    )


def parse_eori_validate(response: httpx.Response) -> EoriValidateResponse:
    return parse(response, _eori_response)
