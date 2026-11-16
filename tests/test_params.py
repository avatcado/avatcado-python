from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Tuple

import httpx
import pytest
import respx

from avatcado import AsyncAvatcado, Avatcado
from tests.conftest import BASE_URL, MOCK_API_KEY

META = {
    "request_id": "req_1",
    "source": "vies",
    "source_status": "live",
    "cached": False,
    "stale": False,
}
VAT_DATA = {
    "valid": True,
    "vat_number": "DE123456789",
    "country_code": "DE",
    "company": None,
    "requested_at": "2026-11-16T12:00:00Z",
}
VALIDATE = {"data": VAT_DATA, "meta": META}
BATCH = {
    "data": {
        "results": [{"data": VAT_DATA, "meta": META}],
        "summary": {"total": 1, "succeeded": 1, "failed": 0},
    },
    "meta": {"request_id": "req_1"},
}
ASYNC_SINGLE = {
    "data": {"request_id": "async_1", "status": "pending", "vat_number": "DE123456789"},
    "meta": {"request_id": "req_1"},
}
ASYNC_BATCH = {
    "data": {"batch_id": "b1", "status": "pending", "total": 1, "accepted": 1, "rejected": []},
    "meta": {"request_id": "req_1"},
}
EORI = {
    "data": {
        "valid": True,
        "eori_number": "GB123456789000",
        "country_code": "GB",
        "company": None,
        "requested_at": "2026-11-16T12:00:00Z",
    },
    "meta": {**META, "source": "hmrc"},
}
RATE = {
    "country_code": "NL",
    "country_name": "Netherlands",
    "currency": "EUR",
    "standard_rate": 21,
    "other_rates": [],
    "updated_at": "2026-01-01T00:00:00.000Z",
}
REQUESTER = "NL123456789B01"


def query(route: respx.Route) -> Dict[str, str]:
    return dict(route.calls.last.request.url.params)


def body(route: respx.Route) -> Dict[str, Any]:
    return json.loads(route.calls.last.request.content)  # type: ignore[no-any-return]


# With requester_vat_number the API turns the cache and the register fallback off unless the
# request says cache=true / fallback=true. The SDK has to send an explicit True, and has to
# stay silent when the caller set nothing, so the API default applies.
class TestValidateFlags:
    @respx.mock(base_url=BASE_URL)
    def test_sends_neither_flag_by_default(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALIDATE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.vat.validate("DE123456789", requester_vat_number=REQUESTER)

        assert query(route) == {"vat_number": "DE123456789", "requester_vat_number": REQUESTER}

    @respx.mock(base_url=BASE_URL)
    def test_sends_cache_true_next_to_a_requester(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALIDATE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.vat.validate("DE123456789", requester_vat_number=REQUESTER, cache=True)

        assert query(route)["cache"] == "true"

    @respx.mock(base_url=BASE_URL)
    def test_sends_cache_false(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALIDATE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.vat.validate("DE123456789", cache=False)

        assert query(route)["cache"] == "false"

    @respx.mock(base_url=BASE_URL)
    def test_sends_fallback(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALIDATE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.vat.validate("DE123456789", fallback=False)
            assert query(route)["fallback"] == "false"
            client.vat.validate("DE123456789", requester_vat_number=REQUESTER, fallback=True)
            assert query(route)["fallback"] == "true"

    @respx.mock(base_url=BASE_URL)
    async def test_async_client_sends_flags(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALIDATE)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.vat.validate("DE123456789")
            assert query(route) == {"vat_number": "DE123456789"}
            await client.vat.validate("DE123456789", cache=True, fallback=False)
            assert query(route)["cache"] == "true"
            assert query(route)["fallback"] == "false"


PostCall = Callable[..., Any]
POSTS: List[Tuple[str, Dict[str, Any], PostCall]] = [
    ("/v1/validate/batch", BATCH, lambda c, **kw: c.vat.validate_batch(["DE123456789"], **kw)),
    (
        "/v1/validate/async",
        ASYNC_SINGLE,
        lambda c, **kw: c.async_vat.validate("DE123456789", **kw),
    ),
    (
        "/v1/validate/async/batch",
        ASYNC_BATCH,
        lambda c, **kw: c.async_vat.validate_batch(["DE123456789"], **kw),
    ),
]


class TestPostBodyFlags:
    @pytest.mark.parametrize(("path", "response", "call"), POSTS, ids=[p for p, _, _ in POSTS])
    @respx.mock(base_url=BASE_URL)
    def test_omits_both_flags_by_default(
        self, respx_mock: respx.MockRouter, path: str, response: Dict[str, Any], call: PostCall
    ) -> None:
        route = respx_mock.post(path).mock(return_value=httpx.Response(200, json=response))
        with Avatcado(MOCK_API_KEY) as client:
            call(client)

        assert "cache" not in body(route)
        assert "fallback" not in body(route)

    @pytest.mark.parametrize(("path", "response", "call"), POSTS, ids=[p for p, _, _ in POSTS])
    @respx.mock(base_url=BASE_URL)
    def test_sends_explicit_booleans(
        self, respx_mock: respx.MockRouter, path: str, response: Dict[str, Any], call: PostCall
    ) -> None:
        route = respx_mock.post(path).mock(return_value=httpx.Response(200, json=response))
        with Avatcado(MOCK_API_KEY) as client:
            call(client, cache=True, fallback=False)
            assert body(route)["cache"] is True
            assert body(route)["fallback"] is False
            call(client, cache=False, fallback=True)
            assert body(route)["cache"] is False
            assert body(route)["fallback"] is True

    @pytest.mark.parametrize(("path", "response", "call"), POSTS, ids=[p for p, _, _ in POSTS])
    @respx.mock(base_url=BASE_URL)
    async def test_async_client_sends_explicit_booleans(
        self, respx_mock: respx.MockRouter, path: str, response: Dict[str, Any], call: PostCall
    ) -> None:
        route = respx_mock.post(path).mock(return_value=httpx.Response(200, json=response))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await call(client)
            assert "cache" not in body(route)
            await call(client, cache=True, fallback=False)
            assert body(route)["cache"] is True
            assert body(route)["fallback"] is False


class TestEoriCacheFlag:
    @respx.mock(base_url=BASE_URL)
    def test_sends_the_flag_only_when_set(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.eori.validate("GB123456789000")
            assert query(route) == {"eori_number": "GB123456789000"}
            client.eori.validate("GB123456789000", cache=True)
            assert query(route)["cache"] == "true"
            client.eori.validate("GB123456789000", cache=False)
            assert query(route)["cache"] == "false"


class TestRatesRequestId:
    @respx.mock(base_url=BASE_URL)
    def test_list_sends_request_id(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(
                200, json={"data": [RATE], "meta": {"request_id": "r", "count": 1}}
            )
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.rates.list()
            assert "x-request-id" not in route.calls.last.request.headers
            client.rates.list(request_id="my-trace-1")
            assert route.calls.last.request.headers["x-request-id"] == "my-trace-1"

    @respx.mock(base_url=BASE_URL)
    async def test_get_sends_request_id(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(200, json={"data": RATE, "meta": {"request_id": "r"}})
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.rates.get("NL", request_id="my-trace-2")
            assert route.calls.last.request.headers["x-request-id"] == "my-trace-2"
        async with AsyncAvatcado(MOCK_API_KEY) as aclient:
            await aclient.rates.get("NL", request_id="my-trace-3")
            assert route.calls.last.request.headers["x-request-id"] == "my-trace-3"
