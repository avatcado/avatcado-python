from __future__ import annotations

import warnings
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any, Awaitable, Callable, Dict, List, Tuple

import httpx
import pytest
import respx

from avatcado import AsyncAvatcado, Avatcado, AvatcadoError, RateLimitError, UpstreamError
from tests.conftest import BASE_URL, MOCK_API_KEY

HEADERS = {"x-request-id": "req_header"}

SyncCall = Callable[[Avatcado], Any]
AsyncCall = Callable[[AsyncAvatcado], Awaitable[Any]]

# (name, HTTP method, path, call) for every method that parses a 2xx body.
SYNC_CALLS: List[Tuple[str, str, str, SyncCall]] = [
    ("vat.validate", "GET", "/v1/validate", lambda c: c.vat.validate("DE123456789")),
    (
        "vat.validate_batch",
        "POST",
        "/v1/validate/batch",
        lambda c: c.vat.validate_batch(["DE123456789"]),
    ),
    (
        "async_vat.validate",
        "POST",
        "/v1/validate/async",
        lambda c: c.async_vat.validate("DE123456789"),
    ),
    (
        "async_vat.validate_batch",
        "POST",
        "/v1/validate/async/batch",
        lambda c: c.async_vat.validate_batch(["DE123456789"]),
    ),
    ("rates.list", "GET", "/v1/rates", lambda c: c.rates.list()),
    ("rates.get", "GET", "/v1/rates/NL", lambda c: c.rates.get("NL")),
    ("eori.validate", "GET", "/v1/eori/validate", lambda c: c.eori.validate("GB123456789000")),
]

ASYNC_CALLS: List[Tuple[str, str, str, AsyncCall]] = [
    ("vat.validate", "GET", "/v1/validate", lambda c: c.vat.validate("DE123456789")),
    (
        "vat.validate_batch",
        "POST",
        "/v1/validate/batch",
        lambda c: c.vat.validate_batch(["DE123456789"]),
    ),
    (
        "async_vat.validate",
        "POST",
        "/v1/validate/async",
        lambda c: c.async_vat.validate("DE123456789"),
    ),
    (
        "async_vat.validate_batch",
        "POST",
        "/v1/validate/async/batch",
        lambda c: c.async_vat.validate_batch(["DE123456789"]),
    ),
    ("rates.list", "GET", "/v1/rates", lambda c: c.rates.list()),
    ("rates.get", "GET", "/v1/rates/NL", lambda c: c.rates.get("NL")),
    ("eori.validate", "GET", "/v1/eori/validate", lambda c: c.eori.validate("GB123456789000")),
]

# 2xx bodies that are valid JSON but not the documented shape.
MALFORMED_BODIES: List[Any] = [
    None,
    [],
    "ok",
    {},
    {"meta": {"request_id": "req_1"}},
    {"data": None, "meta": {"request_id": "req_1"}},
    {"data": "nope", "meta": {"request_id": "req_1"}},
    {"data": {}, "meta": None},
]


def _ids(calls: List[Tuple[str, str, str, Any]]) -> List[str]:
    return [name for name, _, _, _ in calls]


# Every method raises AvatcadoError and nothing else. A 2xx body that does not have the
# documented shape must surface as a parse_error, never as a KeyError or TypeError.
class TestMalformedSuccessBodies:
    @pytest.mark.parametrize("body", MALFORMED_BODIES, ids=repr)
    @pytest.mark.parametrize(("name", "method", "path", "call"), SYNC_CALLS, ids=_ids(SYNC_CALLS))
    @respx.mock(base_url=BASE_URL)
    def test_sync_raises_parse_error(
        self,
        respx_mock: respx.MockRouter,
        name: str,
        method: str,
        path: str,
        call: SyncCall,
        body: Any,
    ) -> None:
        respx_mock.request(method, path).mock(
            return_value=httpx.Response(200, json=body, headers=HEADERS)
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            call(client)

        assert exc_info.value.code == "parse_error"
        assert exc_info.value.status_code == 200
        assert exc_info.value.request_id == "req_header"

    @pytest.mark.parametrize("body", [None, {}, {"data": "nope", "meta": {"request_id": "r"}}])
    @pytest.mark.parametrize(
        ("name", "method", "path", "call"), ASYNC_CALLS, ids=_ids(ASYNC_CALLS)
    )
    @respx.mock(base_url=BASE_URL)
    async def test_async_raises_parse_error(
        self,
        respx_mock: respx.MockRouter,
        name: str,
        method: str,
        path: str,
        call: AsyncCall,
        body: Any,
    ) -> None:
        respx_mock.request(method, path).mock(
            return_value=httpx.Response(200, json=body, headers=HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await call(client)

        assert exc_info.value.code == "parse_error"
        assert exc_info.value.status_code == 200
        assert exc_info.value.request_id == "req_header"

    @respx.mock(base_url=BASE_URL)
    def test_batch_item_that_is_not_an_object(self, respx_mock: respx.MockRouter) -> None:
        body = {
            "data": {"results": ["oops"], "summary": {"total": 1, "succeeded": 0, "failed": 1}},
            "meta": {"request_id": "req_1"},
        }
        respx_mock.post("/v1/validate/batch").mock(return_value=httpx.Response(200, json=body))
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate_batch(["DE123456789"])

        assert exc_info.value.code == "parse_error"

    @respx.mock(base_url=BASE_URL)
    def test_names_the_missing_field(self, respx_mock: respx.MockRouter) -> None:
        body: Dict[str, Any] = {"data": {"valid": True}, "meta": {"request_id": "req_1"}}
        respx_mock.get("/v1/validate").mock(return_value=httpx.Response(200, json=body))
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("DE123456789")

        assert "vat_number" in exc_info.value.message


def error_body(code: str) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": "nope",
            "docs_url": f"https://docs.avatcado.com/errors/{code}",
        },
        "meta": {"request_id": "req_err"},
    }


# A gateway in front of the API answers a timed-out function with an HTML page. The request
# id and Retry-After headers are still there and must survive.
class TestErrorsWithoutJsonBody:
    @respx.mock(base_url=BASE_URL)
    def test_keeps_request_id_and_retry_after(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                504,
                text="<html>Gateway Timeout</html>",
                headers={"x-request-id": "req_gateway", "retry-after": "7"},
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("DE123456789")

        assert exc_info.value.code == "unknown_error"
        assert exc_info.value.status_code == 504
        assert exc_info.value.request_id == "req_gateway"
        assert exc_info.value.retry_after == 7

    @respx.mock(base_url=BASE_URL)
    async def test_async_keeps_request_id(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(502, text="Bad Gateway", headers=HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.list()

        assert exc_info.value.code == "unknown_error"
        assert exc_info.value.request_id == "req_header"


class TestRetryAfterOnErrors:
    @respx.mock(base_url=BASE_URL)
    def test_set_on_base_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(
                503, json=error_body("internal_error"), headers={"retry-after": "5"}
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.rates.list()

        assert type(exc_info.value) is AvatcadoError
        assert exc_info.value.retry_after == 5

    @respx.mock(base_url=BASE_URL)
    def test_none_without_header(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/XX").mock(
            return_value=httpx.Response(404, json=error_body("not_found"))
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.rates.get("XX")

        assert exc_info.value.retry_after is None

    @respx.mock(base_url=BASE_URL)
    def test_none_on_client_side_errors(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(side_effect=httpx.ConnectError("refused"))
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.rates.list()

        assert exc_info.value.code == "network_error"
        assert exc_info.value.retry_after is None

    @pytest.mark.parametrize("value", ["soon", "nan", "inf", "-5", ""])
    @respx.mock(base_url=BASE_URL)
    def test_unusable_header_is_none(self, respx_mock: respx.MockRouter, value: str) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                429, json=error_body("burst_limit_exceeded"), headers={"retry-after": value}
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(RateLimitError) as exc_info:
            client.vat.validate("DE123456789")

        assert exc_info.value.retry_after is None

    @respx.mock(base_url=BASE_URL)
    def test_http_date_becomes_seconds_from_now(self, respx_mock: respx.MockRouter) -> None:
        when = datetime.now(timezone.utc) + timedelta(seconds=30)
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json=error_body("upstream_unavailable"),
                headers={"retry-after": format_datetime(when, usegmt=True)},
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(UpstreamError) as exc_info:
            client.vat.validate("DE123456789")

        assert exc_info.value.retry_after is not None
        assert 27 <= exc_info.value.retry_after <= 31


# Keys minted before the rebrand start with "vtly_" and the API accepts them forever.
class TestLegacyKeyPrefix:
    @pytest.mark.parametrize("key", ["vtly_live_abc123", "vtly_test_abc123"])
    def test_no_warning_for_legacy_keys(self, key: str) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            Avatcado(key).close()

        assert caught == []
