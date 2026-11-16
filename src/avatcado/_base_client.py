from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar

import httpx

from avatcado._config import AvatcadoConfig
from avatcado._errors import AvatcadoError, _raise_for_error, parse_retry_after
from avatcado._types import RateLimitInfo
from avatcado._version import __version__

T = TypeVar("T")

_BACKOFF_BASE = 0.5
_BACKOFF_CAP = 8.0

# Module-level so tests can replace them and no test really waits.
_sleep = time.sleep
_async_sleep = asyncio.sleep


@dataclass(frozen=True)
class Call:
    """One API request, built by ``_operations`` and sent by ``request`` / ``arequest``."""

    method: str
    path: str
    params: Optional[Dict[str, str]] = None
    json: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


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
        retry_after=parse_retry_after(headers),
        burst_limit=_parse_int_header(headers, "x-burst-limit"),
        burst_remaining=_parse_int_header(headers, "x-burst-remaining"),
    )


def raise_for_status(response: httpx.Response) -> None:
    """Raise the matching ``AvatcadoError`` for a 4xx or 5xx response."""
    if response.status_code < 400:
        return
    try:
        body: Any = response.json()
    except Exception:
        # No JSON body: a gateway answered instead of the API. The headers still identify
        # the request.
        error = AvatcadoError(
            f"HTTP {response.status_code}: {response.reason_phrase}",
            code="unknown_error",
            status_code=response.status_code,
            request_id=response.headers.get("x-request-id"),
        )
        error.retry_after = parse_retry_after(response.headers)
        raise error
    _raise_for_error(response.status_code, body, response.headers)


def _parse_error(message: str, response: httpx.Response) -> AvatcadoError:
    return AvatcadoError(
        message,
        code="parse_error",
        status_code=response.status_code,
        request_id=response.headers.get("x-request-id"),
    )


def json_body(response: httpx.Response) -> Dict[str, Any]:
    """The JSON object of a 2xx response, or a ``parse_error``."""
    try:
        body = response.json()
    except Exception:
        raise _parse_error(
            f"Expected JSON response but received unparseable body (HTTP {response.status_code})",
            response,
        )
    if not isinstance(body, dict):
        raise _parse_error(
            f"Expected a JSON object but received {type(body).__name__} "
            f"(HTTP {response.status_code})",
            response,
        )
    return body


def handle_response(response: httpx.Response) -> Dict[str, Any]:
    raise_for_status(response)
    return json_body(response)


def parse(response: httpx.Response, build: Callable[[Dict[str, Any], httpx.Response], T]) -> T:
    """Turn a 2xx response into a typed result.

    A body that does not have the documented shape raises ``AvatcadoError`` with code
    ``parse_error``, carrying the HTTP status and request id, never a bare ``KeyError`` or
    ``TypeError``.
    """
    body = json_body(response)
    try:
        return build(body, response)
    except AvatcadoError as error:
        if error.code == "parse_error" and error.status_code == 0:
            error.status_code = response.status_code
            error.request_id = response.headers.get("x-request-id")
        raise
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise _parse_error(f"Unexpected response shape: {exc!r}", response) from exc


def retry_delay(
    error: AvatcadoError, idempotent: bool, attempt: int, max_retry_delay: float
) -> Optional[float]:
    """Seconds to wait before retrying ``error``, or ``None`` when it must not be retried.

    A burst-limit 429 and a 503 are answers from the API saying the request was not processed,
    so they are retried on every method. A timeout, a network error, a 502 and a 504 leave open
    whether the request was processed, so they are retried only when the request is safe to
    repeat (GET).
    """
    not_processed = (
        error.status_code == 429 and error.code == "burst_limit_exceeded"
    ) or error.status_code == 503
    outcome_unknown = error.code in ("timeout", "network_error") or error.status_code in (502, 504)
    if not not_processed and not (idempotent and outcome_unknown):
        return None

    if error.retry_after is not None:
        return error.retry_after if error.retry_after <= max_retry_delay else None
    backoff: float = min(_BACKOFF_CAP, _BACKOFF_BASE * 2**attempt)
    return min(backoff / 2 + random.random() * (backoff / 2), max_retry_delay)


def _transport_error(exc: httpx.HTTPError, config: AvatcadoConfig) -> AvatcadoError:
    if isinstance(exc, httpx.TimeoutException):
        return AvatcadoError(
            f"Request timed out after {config.timeout}s", code="timeout", status_code=0
        )
    return AvatcadoError(str(exc), code="network_error", status_code=0)


def _next_delay(error: AvatcadoError, call: Call, attempt: int, config: AvatcadoConfig) -> float:
    """The wait before the next attempt; re-raises ``error`` when there is none."""
    if attempt >= config.max_retries:
        raise error
    delay = retry_delay(error, call.method == "GET", attempt, config.max_retry_delay)
    if delay is None:
        raise error
    return delay


def request(http: httpx.Client, config: AvatcadoConfig, call: Call) -> httpx.Response:
    """Send ``call`` and return the 2xx response, retrying when the client is configured to."""
    attempt = 0
    while True:
        try:
            try:
                response = http.request(
                    call.method,
                    call.path,
                    params=call.params,
                    json=call.json,
                    headers=build_headers(config.api_key, call.request_id),
                )
            except httpx.HTTPError as exc:
                raise _transport_error(exc, config) from None
            raise_for_status(response)
            return response
        except AvatcadoError as error:
            delay = _next_delay(error, call, attempt, config)
        attempt += 1
        _sleep(delay)


async def arequest(http: httpx.AsyncClient, config: AvatcadoConfig, call: Call) -> httpx.Response:
    """Async twin of :func:`request`."""
    attempt = 0
    while True:
        try:
            try:
                response = await http.request(
                    call.method,
                    call.path,
                    params=call.params,
                    json=call.json,
                    headers=build_headers(config.api_key, call.request_id),
                )
            except httpx.HTTPError as exc:
                raise _transport_error(exc, config) from None
            raise_for_status(response)
            return response
        except AvatcadoError as error:
            delay = _next_delay(error, call, attempt, config)
        attempt += 1
        await _async_sleep(delay)


def _parse_int_header(headers: httpx.Headers, name: str) -> Optional[int]:
    value = headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
