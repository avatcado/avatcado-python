from __future__ import annotations

import httpx
import pytest
import respx

from avatcado import AuthenticationError, Avatcado, AvatcadoError, RateLimitError
from tests.conftest import (
    BASE_URL,
    GET_RATE_RESPONSE,
    LIST_RATES_RESPONSE,
    MOCK_API_KEY,
    RATE_LIMIT_HEADERS,
)


class TestListRates:
    @respx.mock(base_url=BASE_URL)
    def test_returns_rates(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(200, json=LIST_RATES_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.rates.list()
        assert len(result.data) == 2
        assert result.data[0].country_code == "NL"
        assert result.data[0].standard_rate == 21
        assert len(result.data[0].other_rates) == 2
        assert result.data[0].other_rates[0].rate == 9
        assert result.data[0].other_rates[0].type == "reduced"
        assert result.meta.request_id == "req_rates1"
        assert result.meta.count == 2
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_info(self, respx_mock: respx.MockRouter) -> None:
        headers = {
            "x-ratelimit-limit": "200",
            "x-ratelimit-remaining": "199",
            "x-ratelimit-reset": "2026-04-01T00:00:00Z",
        }
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(200, json=LIST_RATES_RESPONSE, headers=headers)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.rates.list()
        assert result.rate_limit.limit == 200
        assert result.rate_limit.remaining == 199
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_calls_correct_endpoint(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(200, json=LIST_RATES_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.rates.list()
        assert route.called
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_auth_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_r401"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError):
            client.rates.list()
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                    },
                    "meta": {"request_id": "req_r429"},
                },
                headers={"retry-after": "20"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.rates.list()
        assert exc_info.value.retry_after == 20.0
        client.close()


class TestGetRate:
    @respx.mock(base_url=BASE_URL)
    def test_returns_single_rate(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(200, json=GET_RATE_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.rates.get("NL")
        assert result.data.country_code == "NL"
        assert result.data.country_name == "Netherlands"
        assert result.data.currency == "EUR"
        assert result.data.standard_rate == 21
        assert result.meta.request_id == "req_rate_nl"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_calls_correct_endpoint(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(200, json=GET_RATE_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.rates.get("NL")
        assert route.called
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_auth_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_rg401"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError):
            client.rates.get("NL")
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_not_found(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/ZZ").mock(
            return_value=httpx.Response(
                404,
                json={
                    "error": {"message": "Country not found", "code": "not_found"},
                    "meta": {"request_id": "req_rg404"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.rates.get("ZZ")
        assert exc_info.value.code == "not_found"
        assert exc_info.value.status_code == 404
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                    },
                    "meta": {"request_id": "req_rg429"},
                },
                headers={"retry-after": "10"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError):
            client.rates.get("NL")
        client.close()
