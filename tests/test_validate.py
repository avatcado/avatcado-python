from __future__ import annotations

import httpx
import pytest
import respx

from avatcado import (
    AuthenticationError,
    Avatcado,
    AvatcadoError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)
from tests.conftest import BASE_URL, MOCK_API_KEY, RATE_LIMIT_HEADERS, VALID_RESPONSE


class TestValidateSuccess:
    @respx.mock(base_url=BASE_URL)
    def test_returns_valid_response(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.data.valid is True
        assert result.data.vat_number == "NL123456789B01"
        assert result.data.country_code == "NL"
        assert result.data.company is not None
        assert result.data.company.name == "Test BV"
        assert result.data.company.address == "Amsterdam, Netherlands"
        assert result.data.requested_at == "2026-03-18T12:00:00Z"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_consultation_number(self, respx_mock: respx.MockRouter) -> None:
        response = {
            **VALID_RESPONSE,
            "data": {**VALID_RESPONSE["data"], "consultation_number": "WAPIAAAAA1BBBBB"},
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=response, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01", requester_vat_number="DE987654321")
        assert result.data.consultation_number == "WAPIAAAAA1BBBBB"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_null_company(self, respx_mock: respx.MockRouter) -> None:
        response = {**VALID_RESPONSE, "data": {**VALID_RESPONSE["data"], "company": None}}
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=response, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.data.company is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_null_company_address(self, respx_mock: respx.MockRouter) -> None:
        response = {
            **VALID_RESPONSE,
            "data": {
                **VALID_RESPONSE["data"],
                "company": {"name": "Test BV", "address": None},
            },
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=response, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.data.company is not None
        assert result.data.company.address is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_consultation_number_null_when_absent(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.data.consultation_number is None
        client.close()


class TestValidateMeta:
    @respx.mock(base_url=BASE_URL)
    def test_response_meta(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.request_id == "req_abc123"
        assert result.meta.request_duration_ms == 150
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_cached_response(self, respx_mock: respx.MockRouter) -> None:
        cached = {
            "data": VALID_RESPONSE["data"],
            "meta": {
                "request_id": "req_cached",
                "cached": True,
                "cached_at": "2026-03-18T11:00:00Z",
                "stale": False,
                "mode": None,
                "request_duration_ms": 5,
                "source_status": None,
            },
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=cached, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.cached is True
        assert result.meta.cached_at == "2026-03-18T11:00:00Z"
        assert result.meta.stale is False
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_stale_response(self, respx_mock: respx.MockRouter) -> None:
        stale = {
            "data": VALID_RESPONSE["data"],
            "meta": {
                "request_id": "req_stale",
                "cached": True,
                "cached_at": "2026-03-17T11:00:00Z",
                "stale": True,
                "mode": None,
                "request_duration_ms": 2,
                "source_status": "unavailable",
            },
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=stale, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.stale is True
        assert result.meta.source_status == "unavailable"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_test_mode(self, respx_mock: respx.MockRouter) -> None:
        test_resp = {
            "data": VALID_RESPONSE["data"],
            "meta": {
                "request_id": "req_test",
                "mode": "test",
                "cached": None,
                "cached_at": None,
                "stale": None,
                "request_duration_ms": 10,
                "source_status": None,
            },
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=test_resp, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.mode == "test"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_source_status_live(self, respx_mock: respx.MockRouter) -> None:
        resp = {
            "data": VALID_RESPONSE["data"],
            "meta": {**VALID_RESPONSE["meta"], "source_status": "live"},
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=resp, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.source_status == "live"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_source_status_degraded(self, respx_mock: respx.MockRouter) -> None:
        resp = {
            "data": VALID_RESPONSE["data"],
            "meta": {**VALID_RESPONSE["meta"], "source_status": "degraded"},
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=resp, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.meta.source_status == "degraded"
        client.close()


class TestValidateRateLimit:
    @respx.mock(base_url=BASE_URL)
    def test_parses_rate_limit_headers(self, respx_mock: respx.MockRouter) -> None:
        headers = {
            "x-ratelimit-limit": "500",
            "x-ratelimit-remaining": "42",
            "x-ratelimit-reset": "2026-05-01T00:00:00Z",
            "retry-after": "10",
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=headers)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.rate_limit.limit == 500
        assert result.rate_limit.remaining == 42
        assert result.rate_limit.reset == "2026-05-01T00:00:00Z"
        assert result.rate_limit.retry_after == 10.0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_null_for_absent_headers(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(return_value=httpx.Response(200, json=VALID_RESPONSE))
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.rate_limit.limit is None
        assert result.rate_limit.remaining is None
        assert result.rate_limit.reset is None
        assert result.rate_limit.retry_after is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_null_for_malformed_headers(self, respx_mock: respx.MockRouter) -> None:
        headers = {
            "x-ratelimit-limit": "not-a-number",
            "x-ratelimit-remaining": "abc",
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=headers)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.rate_limit.limit is None
        assert result.rate_limit.remaining is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_burst_limit_headers(self, respx_mock: respx.MockRouter) -> None:
        headers = {
            **RATE_LIMIT_HEADERS,
            "x-burst-limit": "20",
            "x-burst-remaining": "15",
        }
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=headers)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.rate_limit.burst_limit == 20
        assert result.rate_limit.burst_remaining == 15
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_null_burst_headers(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate("NL123456789B01")
        assert result.rate_limit.burst_limit is None
        assert result.rate_limit.burst_remaining is None
        client.close()


class TestValidateRequestParams:
    @respx.mock(base_url=BASE_URL)
    def test_sends_cache_false(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01", cache=False)
        assert "cache=false" in str(route.calls[0].request.url)
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_omits_cache_when_true(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01")
        assert "cache" not in str(route.calls[0].request.url)
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_requester_vat_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01", requester_vat_number="DE987654321")
        assert "requester_vat_number=DE987654321" in str(route.calls[0].request.url)
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_request_id_header(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01", request_id="my-trace-id")
        assert route.calls[0].request.headers["x-request-id"] == "my-trace-id"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_auth_header(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01")
        assert route.calls[0].request.headers["authorization"] == f"Bearer {MOCK_API_KEY}"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_user_agent(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("NL123456789B01")
        assert route.calls[0].request.headers["user-agent"].startswith("avatcado-python/")
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_trims_vat_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(200, json=VALID_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate("  NL123456789B01  ")
        assert "vat_number=NL123456789B01" in str(route.calls[0].request.url)
        client.close()


class TestValidateClientSideErrors:
    def test_empty_vat_number(self) -> None:
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError, match="vat_number is required") as exc_info:
            client.vat.validate("")
        assert exc_info.value.code == "missing_parameter"
        client.close()

    def test_whitespace_vat_number(self) -> None:
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError):
            client.vat.validate("   ")
        client.close()


class TestValidateErrors:
    @respx.mock(base_url=BASE_URL)
    def test_authentication_error_401(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_err1"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "unauthorized"
        assert exc_info.value.status_code == 401
        assert exc_info.value.request_id == "req_err1"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_authentication_error_tier_insufficient(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {"message": "Upgrade your plan", "code": "tier_insufficient"},
                    "meta": {"request_id": "req_tier"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "tier_insufficient"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_authentication_error_forbidden(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {"message": "Access forbidden", "code": "forbidden"},
                    "meta": {"request_id": "req_forbidden"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "forbidden"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_authentication_error_key_revoked(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "API key revoked", "code": "key_revoked"},
                    "meta": {"request_id": "req_revoked"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "key_revoked"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_validation_error_invalid_format(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                422,
                json={
                    "error": {"message": "Invalid VAT format", "code": "invalid_vat_format"},
                    "meta": {"request_id": "req_err2"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate("INVALID")
        assert exc_info.value.code == "invalid_vat_format"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_validation_error_with_details(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                422,
                json={
                    "error": {
                        "message": "Validation failed",
                        "code": "validation_error",
                        "details": [{"field": "vat_number", "message": "must be a string"}],
                    },
                    "meta": {"request_id": "req_val"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.details == [{"field": "vat_number", "message": "must be a string"}]
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_validation_error_invalid_json(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {"message": "Invalid JSON body", "code": "invalid_json"},
                    "meta": {"request_id": "req_json"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "invalid_json"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                    },
                    "meta": {"request_id": "req_err3"},
                },
                headers={"retry-after": "30"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.retry_after == 30.0
        assert exc_info.value.status_code == 429
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_burst(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Burst limit exceeded",
                        "code": "burst_limit_exceeded",
                    },
                    "meta": {"request_id": "req_burst"},
                },
                headers={"retry-after": "5"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "burst_limit_exceeded"
        assert exc_info.value.retry_after == 5.0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_upstream_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json={
                    "error": {
                        "message": "VIES is unavailable",
                        "code": "upstream_unavailable",
                    },
                    "meta": {"request_id": "req_err4"},
                },
                headers={"retry-after": "60"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(UpstreamError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.retry_after == 60.0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_upstream_member_state_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json={
                    "error": {
                        "message": "Member state unavailable",
                        "code": "upstream_member_state_unavailable",
                    },
                    "meta": {"request_id": "req_ms"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(UpstreamError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "upstream_member_state_unavailable"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_error_docs_url(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                422,
                json={
                    "error": {
                        "message": "Invalid VAT format",
                        "code": "invalid_vat_format",
                        "docs_url": "https://docs.avatcado.com/errors/invalid_vat_format",
                    },
                    "meta": {"request_id": "req_err5"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate("INVALID")
        assert exc_info.value.docs_url == "https://docs.avatcado.com/errors/invalid_vat_format"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_generic_error_internal(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                500,
                json={
                    "error": {"message": "Internal server error", "code": "internal_error"},
                    "meta": {"request_id": "req_internal"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert not isinstance(exc_info.value, AuthenticationError)
        assert not isinstance(exc_info.value, ValidationError)
        assert exc_info.value.code == "internal_error"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_generic_error_key_limit_reached(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {
                        "message": "Monthly key limit reached",
                        "code": "key_limit_reached",
                    },
                    "meta": {"request_id": "req_limit"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert not isinstance(exc_info.value, AuthenticationError)
        assert exc_info.value.code == "key_limit_reached"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_error_without_details_has_none(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_nodet"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.details is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_request_id_from_header_fallback(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                500,
                json={"error": {"message": "Error", "code": "unknown_error"}},
                headers={"x-request-id": "req_from_header"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.request_id == "req_from_header"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_upstream_error_echoes_request_context(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json={
                    "error": {
                        "code": "upstream_unavailable",
                        "message": "The upstream VAT validation service is unavailable",
                        "docs_url": "https://docs.avatcado.com/errors/upstream_unavailable",
                        "vat_number": "SE556677889901",
                        "requester_vat_number": "NL861234567B01",
                    },
                    "meta": {
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "validation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    },
                },
                headers={"retry-after": "60"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(UpstreamError) as exc_info:
            client.vat.validate("SE556677889901")
        err = exc_info.value
        assert err.vat_number == "SE556677889901"
        assert err.requester_vat_number == "NL861234567B01"
        assert err.validation_id == "7c9e6679-7425-40de-944b-e07fc1f90ae7"
        assert err.request_id == "550e8400-e29b-41d4-a716-446655440000"
        assert err.docs_url == "https://docs.avatcado.com/errors/upstream_unavailable"
        assert err.retry_after == 60.0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_upstream_error_from_older_server_has_none_context(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                503,
                json={
                    "error": {"message": "VIES is unavailable", "code": "upstream_unavailable"},
                    "meta": {"request_id": "req_old_server"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(UpstreamError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.vat_number is None
        assert exc_info.value.requester_vat_number is None
        assert exc_info.value.validation_id is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_error_echoes_vat_number(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                        "vat_number": "NL123456789B01",
                    },
                    "meta": {"request_id": "req_rl_ctx"},
                },
                headers={"retry-after": "30"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.vat_number == "NL123456789B01"
        assert exc_info.value.requester_vat_number is None
        assert exc_info.value.retry_after == 30.0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_validation_error_echoes_vat_number_and_details(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {
                        "message": "Validation failed",
                        "code": "validation_error",
                        "vat_number": "XX000",
                        "details": [
                            {"field": "vat_number", "message": "must match a country format"}
                        ],
                    },
                    "meta": {"request_id": "req_val_ctx"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate("XX000")
        assert exc_info.value.vat_number == "XX000"
        assert exc_info.value.details == [
            {"field": "vat_number", "message": "must match a country format"}
        ]
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_authentication_error_has_none_request_context(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"message": "Invalid API key", "code": "unauthorized"},
                    "meta": {"request_id": "req_auth_ctx"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.vat_number is None
        assert exc_info.value.requester_vat_number is None
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_internal_error_echoes_vat_number_on_base_class(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                500,
                json={
                    "error": {
                        "message": "Internal server error",
                        "code": "internal_error",
                        "vat_number": "NL123456789B01",
                    },
                    "meta": {"request_id": "req_500_ctx"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert type(exc_info.value) is AvatcadoError
        assert exc_info.value.vat_number == "NL123456789B01"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_validation_id_is_not_exposed_on_non_upstream_errors(
        self, respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {"message": "Rate limit exceeded", "code": "rate_limit_exceeded"},
                    "meta": {"request_id": "req_rl_vid", "validation_id": "should-be-ignored"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert not hasattr(exc_info.value, "validation_id")
        client.close()


class TestValidateNetworkErrors:
    @respx.mock(base_url=BASE_URL)
    def test_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(side_effect=httpx.ReadTimeout("timed out"))
        client = Avatcado(MOCK_API_KEY, timeout=1.0)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "timeout"
        assert exc_info.value.status_code == 0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_network_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(side_effect=httpx.ConnectError("connection refused"))
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "network_error"
        assert exc_info.value.status_code == 0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_non_json_200(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(
                200,
                text="<html>Gateway OK</html>",
                headers={"x-request-id": "req_proxy"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "parse_error"
        assert exc_info.value.status_code == 200
        assert exc_info.value.request_id == "req_proxy"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_non_json_502(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.get("/v1/validate").mock(
            return_value=httpx.Response(502, text="<html>Bad Gateway</html>")
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate("NL123456789B01")
        assert exc_info.value.code == "unknown_error"
        assert exc_info.value.status_code == 502
        client.close()
