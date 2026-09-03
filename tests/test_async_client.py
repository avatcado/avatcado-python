from __future__ import annotations

import httpx
import pytest
import respx

from avatcado import (
    AsyncAvatcado,
    AuthenticationError,
    AvatcadoError,
    RateLimitError,
    UpstreamError,
    ValidationError,
    is_batch_success,
)
from tests.conftest import (
    BASE_URL,
    BATCH_RESPONSE,
    GET_RATE_RESPONSE,
    LIST_RATES_RESPONSE,
    MOCK_API_KEY,
    RATE_LIMIT_HEADERS,
    VALID_RESPONSE,
)


class TestAsyncValidate:
    @respx.mock(base_url=BASE_URL)
    async def test_validate_success(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.vat.validate("NL123456789B01")
            assert result.data.valid is True
            assert result.data.vat_number == "NL123456789B01"
            assert result.data.company is not None
            assert result.meta.request_id == "req_abc123"
            assert result.meta.source == "vies"
            assert result.rate_limit.limit == 100

    @respx.mock(base_url=BASE_URL)
    async def test_validate_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_async_err"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.vat.validate("NL123456789B01")
            assert exc_info.value.code == "unauthorized"

    async def test_validate_empty_raises(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError):
                await client.vat.validate("")

    @respx.mock(base_url=BASE_URL)
    async def test_validate_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(side_effect=httpx.ReadTimeout("timed out"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.vat.validate("NL123456789B01")
            assert exc_info.value.code == "timeout"

    @respx.mock(base_url=BASE_URL)
    async def test_validate_upstream_error_echoes_context(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json={
                    "error": {
                        "code": "upstream_unavailable",
                        "message": "Upstream unavailable",
                        "vat_number": "SE556677889901",
                        "requester_vat_number": "NL861234567B01",
                    },
                    "meta": {
                        "request_id": "req_async_up",
                        "validation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    },
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(UpstreamError) as exc_info:
                await client.vat.validate("SE556677889901")
            assert exc_info.value.vat_number == "SE556677889901"
            assert exc_info.value.requester_vat_number == "NL861234567B01"
            assert exc_info.value.validation_id == "7c9e6679-7425-40de-944b-e07fc1f90ae7"


class TestAsyncBatch:
    @respx.mock(base_url=BASE_URL)
    async def test_batch_success(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.vat.validate_batch(["NL123456789B01", "DE987654321"])
            assert len(result.results) == 2
            assert result.summary.total == 2
            assert all(is_batch_success(r) for r in result.results)

    async def test_batch_empty_raises(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError):
                await client.vat.validate_batch([])

    async def test_batch_exceeds_50_raises(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError):
                await client.vat.validate_batch([f"NL{i:09d}B01" for i in range(51)])

    @respx.mock(base_url=BASE_URL)
    async def test_batch_rate_limit_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                    },
                    "meta": {"request_id": "req_async_rl"},
                },
                headers={"retry-after": "10"},
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client.vat.validate_batch(["NL123456789B01"])
            assert exc_info.value.retry_after == 10.0


class TestAsyncRates:
    @respx.mock(base_url=BASE_URL)
    async def test_list_rates(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(
            return_value=httpx.Response(200, json=LIST_RATES_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.rates.list()
            assert len(result.data) == 2
            assert result.data[0].country_code == "NL"

    @respx.mock(base_url=BASE_URL)
    async def test_get_rate(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(
            return_value=httpx.Response(200, json=GET_RATE_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.rates.get("NL")
            assert result.data.country_code == "NL"
            assert result.data.standard_rate == 21

    @respx.mock(base_url=BASE_URL)
    async def test_get_rate_not_found(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/ZZ").mock(
            return_value=httpx.Response(
                404,
                json={
                    "error": {"message": "Country not found", "code": "not_found"},
                    "meta": {"request_id": "req_async_404"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.get("ZZ")
            assert exc_info.value.code == "not_found"


class TestAsyncRatesErrors:
    @respx.mock(base_url=BASE_URL)
    async def test_list_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(side_effect=httpx.ReadTimeout("timed out"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.list()
            assert exc_info.value.code == "timeout"

    @respx.mock(base_url=BASE_URL)
    async def test_get_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(side_effect=httpx.ReadTimeout("timed out"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.get("NL")
            assert exc_info.value.code == "timeout"

    @respx.mock(base_url=BASE_URL)
    async def test_list_connection_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates").mock(side_effect=httpx.ConnectError("refused"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.list()
            assert exc_info.value.code == "network_error"

    @respx.mock(base_url=BASE_URL)
    async def test_get_connection_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/rates/NL").mock(side_effect=httpx.ConnectError("refused"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.rates.get("NL")
            assert exc_info.value.code == "network_error"


class TestAsyncContextManager:
    async def test_aenter_aexit(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            assert client.vat is not None
            assert client.rates is not None
