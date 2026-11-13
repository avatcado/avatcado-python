from __future__ import annotations

from typing import Any, Dict

import httpx
import pytest
import respx

from avatcado import (
    AsyncAvatcado,
    Avatcado,
    AvatcadoError,
    EoriResponseMeta,
    EoriValidationResult,
    RateLimitError,
    UpstreamError,
    ValidationError,
)
from tests.conftest import BASE_URL, MOCK_API_KEY, RATE_LIMIT_HEADERS

# The wire shape GET /v1/eori/validate returns.
EORI_RESPONSE: Dict[str, Any] = {
    "data": {
        "valid": True,
        "eori_number": "GB123456789000",
        "country_code": "GB",
        "company": {"name": "EXAMPLE TRADING LTD", "address": "1 HIGH STREET, LONDON, SW1A 1AA"},
        "requested_at": "2026-11-13T09:19:29.000Z",
    },
    "meta": {
        "request_id": "req_eori_1",
        "request_duration_ms": 312,
        "source": "hmrc",
        "source_status": "live",
        "cached": False,
        "stale": False,
    },
}


def error_body(code: str, message: str, **extra: Any) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "docs_url": f"https://docs.avatcado.com/errors/{code}",
            **extra,
        },
        "meta": {"request_id": "req_eori_err"},
    }


class TestEoriValidate:
    @respx.mock(base_url=BASE_URL)
    def test_returns_result_meta_and_rate_limit(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        with Avatcado(MOCK_API_KEY) as client:
            result = client.eori.validate("GB123456789000")

        assert route.calls.last.request.url.params["eori_number"] == "GB123456789000"
        assert "cache" not in route.calls.last.request.url.params
        assert result.data.valid is True
        assert result.data.eori_number == "GB123456789000"
        assert result.data.country_code == "GB"
        assert result.data.company is not None
        assert result.data.company.name == "EXAMPLE TRADING LTD"
        assert result.data.company.address == "1 HIGH STREET, LONDON, SW1A 1AA"
        assert result.data.requested_at == "2026-11-13T09:19:29.000Z"
        assert result.meta.request_id == "req_eori_1"
        assert result.meta.request_duration_ms == 312
        assert result.meta.source == "hmrc"
        assert result.meta.source_status == "live"
        assert result.meta.cached is False
        assert result.meta.stale is False
        assert result.meta.cached_at is None
        assert result.meta.mode is None
        assert result.rate_limit.limit == 100

    @respx.mock(base_url=BASE_URL)
    def test_trims_the_number_and_leaves_normalization_to_the_api(
        self, respx_mock: respx.MockRouter
    ) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI_RESPONSE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.eori.validate("  gb 123.456.789 000 ")

        assert route.calls.last.request.url.params["eori_number"] == "gb 123.456.789 000"

    @respx.mock(base_url=BASE_URL)
    def test_sends_cache_false_only_when_the_cache_is_off(
        self, respx_mock: respx.MockRouter
    ) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI_RESPONSE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.eori.validate("GB123456789000", cache=False)
            assert route.calls.last.request.url.params["cache"] == "false"
            client.eori.validate("GB123456789000", cache=True)
            assert "cache" not in route.calls.last.request.url.params

    @respx.mock(base_url=BASE_URL)
    def test_forwards_a_request_id(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI_RESPONSE)
        )
        with Avatcado(MOCK_API_KEY) as client:
            client.eori.validate("GB123456789000", request_id="my-trace-1")

        assert route.calls.last.request.headers["x-request-id"] == "my-trace-1"

    @respx.mock(base_url=BASE_URL)
    def test_company_is_none_when_the_holder_published_no_details(
        self, respx_mock: respx.MockRouter
    ) -> None:
        body = {**EORI_RESPONSE, "data": {**EORI_RESPONSE["data"], "company": None}}
        respx_mock.get("/v1/eori/validate").mock(return_value=httpx.Response(200, json=body))
        with Avatcado(MOCK_API_KEY) as client:
            result = client.eori.validate("GB123456789000")

        assert result.data.valid is True
        assert result.data.company is None

    @respx.mock(base_url=BASE_URL)
    def test_reports_a_stored_answer_served_during_an_outage(
        self, respx_mock: respx.MockRouter
    ) -> None:
        body = {
            **EORI_RESPONSE,
            "meta": {
                **EORI_RESPONSE["meta"],
                "source": "ec_eos",
                "source_status": "unavailable",
                "cached": True,
                "stale": True,
                "cached_at": "2026-10-01T08:00:00.000Z",
            },
        }
        respx_mock.get("/v1/eori/validate").mock(return_value=httpx.Response(200, json=body))
        with Avatcado(MOCK_API_KEY) as client:
            result = client.eori.validate("IT01234567890")

        assert result.meta.source == "ec_eos"
        assert result.meta.source_status == "unavailable"
        assert result.meta.cached is True
        assert result.meta.stale is True
        assert result.meta.cached_at == "2026-10-01T08:00:00.000Z"

    @respx.mock(base_url=BASE_URL)
    def test_reports_test_mode(self, respx_mock: respx.MockRouter) -> None:
        meta = {**EORI_RESPONSE["meta"], "mode": "test", "source": "test"}
        body = {**EORI_RESPONSE, "meta": meta}
        respx_mock.get("/v1/eori/validate").mock(return_value=httpx.Response(200, json=body))
        with Avatcado("avat_test_key") as client:
            result = client.eori.validate("NL111111111")

        assert result.meta.mode == "test"
        assert result.meta.source == "test"

    @pytest.mark.parametrize("value", ["", "   "])
    @respx.mock(base_url=BASE_URL, assert_all_called=False)
    def test_rejects_an_empty_number_without_calling_the_api(
        self, respx_mock: respx.MockRouter, value: str
    ) -> None:
        route = respx_mock.get("/v1/eori/validate")
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(ValidationError) as exc_info:
            client.eori.validate(value)

        assert exc_info.value.code == "missing_parameter"
        assert exc_info.value.message == "eori_number is required"
        assert not route.called

    @respx.mock(base_url=BASE_URL)
    def test_invalid_format_raises_validation_error_with_the_echoed_number(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(
                422,
                json=error_body(
                    "invalid_eori_format",
                    "Invalid EORI number format: GB123. "
                    "GB EORI numbers are GB followed by 12 to 15 digits",
                    eori_number="GB123",
                ),
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(ValidationError) as exc_info:
            client.eori.validate("gb123")

        error = exc_info.value
        assert error.code == "invalid_eori_format"
        assert error.status_code == 422
        assert error.eori_number == "GB123"
        assert error.vat_number is None
        assert error.docs_url == "https://docs.avatcado.com/errors/invalid_eori_format"
        assert error.request_id == "req_eori_err"

    @respx.mock(base_url=BASE_URL)
    def test_register_outage_raises_upstream_error_with_retry_after(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(
                503,
                json=error_body(
                    "upstream_unavailable",
                    "The HMRC EORI service is unavailable",
                    eori_number="GB123456789000",
                ),
                headers={"retry-after": "60"},
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(UpstreamError) as exc_info:
            client.eori.validate("GB123456789000")

        assert exc_info.value.retry_after == 60
        assert exc_info.value.validation_id is None
        assert exc_info.value.eori_number == "GB123456789000"

    @respx.mock(base_url=BASE_URL)
    def test_quota_exhausted_raises_rate_limit_error_with_the_echoed_number(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(
                429,
                json=error_body(
                    "rate_limit_exceeded",
                    "Monthly limit of 500 requests exceeded",
                    eori_number="GB123456789000",
                ),
                headers={"retry-after": "3600"},
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(RateLimitError) as exc_info:
            client.eori.validate("GB123456789000")

        assert exc_info.value.retry_after == 3600
        assert exc_info.value.eori_number == "GB123456789000"

    @respx.mock(base_url=BASE_URL)
    def test_missing_data_raises_parse_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json={"meta": {"request_id": "req_x"}})
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.eori.validate("GB123456789000")

        assert exc_info.value.code == "parse_error"

    @respx.mock(base_url=BASE_URL)
    def test_timeout_raises_timeout_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/eori/validate").mock(side_effect=httpx.ReadTimeout("timed out"))
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(AvatcadoError) as exc_info:
            client.eori.validate("GB123456789000")

        assert exc_info.value.code == "timeout"

    @respx.mock(base_url=BASE_URL)
    def test_vat_errors_leave_eori_number_none(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                422,
                json={
                    "error": {
                        "code": "invalid_vat_format",
                        "message": "Invalid VAT number format",
                        "vat_number": "DE123",
                    },
                    "meta": {"request_id": "req_vat_err"},
                },
            )
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(ValidationError) as exc_info:
            client.vat.validate("DE123")

        assert exc_info.value.vat_number == "DE123"
        assert exc_info.value.eori_number is None


class TestEoriTypes:
    def test_result_from_dict_requires_the_core_fields(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            EoriValidationResult.from_dict({"valid": True})

        assert exc_info.value.code == "parse_error"

    def test_meta_defaults_every_optional_field_to_none(self) -> None:
        meta = EoriResponseMeta.from_dict({"request_id": "req_min"})

        assert meta == EoriResponseMeta(request_id="req_min")
        assert meta.source is None
        assert meta.source_status is None
        assert meta.cached is None
        assert meta.stale is None
        assert meta.cached_at is None
        assert meta.mode is None
        assert meta.request_duration_ms is None

    def test_meta_requires_a_request_id(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            EoriResponseMeta.from_dict({})

        assert exc_info.value.code == "parse_error"


class TestAsyncEoriValidate:
    @respx.mock(base_url=BASE_URL)
    async def test_returns_result(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(200, json=EORI_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.eori.validate("GB123456789000", cache=False, request_id="t-1")

        params = route.calls.last.request.url.params
        assert params["eori_number"] == "GB123456789000"
        assert params["cache"] == "false"
        assert route.calls.last.request.headers["x-request-id"] == "t-1"
        assert result.data.eori_number == "GB123456789000"
        assert result.meta.source == "hmrc"
        assert result.rate_limit.limit == 100

    @respx.mock(base_url=BASE_URL, assert_all_called=False)
    async def test_rejects_an_empty_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/eori/validate")
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError) as exc_info:
                await client.eori.validate(" ")

        assert exc_info.value.code == "missing_parameter"
        assert not route.called

    @respx.mock(base_url=BASE_URL)
    async def test_error_carries_the_echoed_number(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/eori/validate").mock(
            return_value=httpx.Response(
                503,
                json=error_body(
                    "upstream_unavailable",
                    "The EU EORI validation service is unavailable",
                    eori_number="NL123456789",
                ),
                headers={"retry-after": "60"},
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(UpstreamError) as exc_info:
                await client.eori.validate("NL123456789")

        assert exc_info.value.eori_number == "NL123456789"
        assert exc_info.value.retry_after == 60

    @respx.mock(base_url=BASE_URL)
    async def test_timeout_raises_timeout_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/eori/validate").mock(side_effect=httpx.ReadTimeout("timed out"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.eori.validate("NL123456789")

        assert exc_info.value.code == "timeout"
