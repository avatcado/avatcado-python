from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from avatcado._errors import AvatcadoError, _raise_for_error
from avatcado._types import RateLimitInfo
from avatcado._version import __version__


def build_headers(api_key: str, request_id: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"avatcado-python/{__version__}",
    }
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


def parse_rate_limit(headers: httpx.Headers) -> RateLimitInfo:
    return RateLimitInfo(
        limit=_parse_int_header(headers, "x-ratelimit-limit"),
        remaining=_parse_int_header(headers, "x-ratelimit-remaining"),
        reset=headers.get("x-ratelimit-reset"),
        retry_after=_parse_float_header(headers, "retry-after"),
        burst_limit=_parse_int_header(headers, "x-burst-limit"),
        burst_remaining=_parse_int_header(headers, "x-burst-remaining"),
    )


def handle_response(response: httpx.Response) -> Dict[str, Any]:
    if response.status_code >= 400:
        body: Any = None
        try:
            body = response.json()
        except Exception:
            raise AvatcadoError(
                f"HTTP {response.status_code}: {response.reason_phrase}",
                code="unknown_error",
                status_code=response.status_code,
                request_id=None,
            )
        _raise_for_error(response.status_code, body, response.headers)

    try:
        return response.json()  # type: ignore[no-any-return]
    except Exception:
        raise AvatcadoError(
            f"Expected JSON response but received unparseable body (HTTP {response.status_code})",
            code="parse_error",
            status_code=response.status_code,
            request_id=response.headers.get("x-request-id"),
        )


def _parse_int_header(headers: httpx.Headers, name: str) -> Optional[int]:
    value = headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float_header(headers: httpx.Headers, name: str) -> Optional[float]:
    value = headers.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
