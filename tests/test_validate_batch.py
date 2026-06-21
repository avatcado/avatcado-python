from __future__ import annotations

import json

import httpx
import pytest
import respx

from avatcado import (
    AuthenticationError,
    Avatcado,
    AvatcadoError,
    RateLimitError,
    ValidationError,
    is_batch_success,
)
from tests.conftest import BASE_URL, BATCH_RESPONSE, MOCK_API_KEY, RATE_LIMIT_HEADERS


class TestBatchValidateSuccess:
    @respx.mock(base_url=BASE_URL)
    def test_validates_batch(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate_batch(["NL123456789B01", "DE987654321"])
        assert len(result.results) == 2
        assert result.summary.total == 2
        assert result.summary.succeeded == 2
        assert result.summary.failed == 0
        body = json.loads(route.calls[0].request.content)
        assert body["vat_numbers"] == ["NL123456789B01", "DE987654321"]
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_mixed_results(self, respx_mock: respx.MockRouter) -> None:
        mixed = {
            "data": {
                "results": [
                    {
                        "data": {
                            "valid": True,
                            "vat_number": "NL123456789B01",
                            "country_code": "NL",
                            "company": {"name": "Test BV", "address": "Amsterdam"},
                            "consultation_number": None,
                            "requested_at": "2026-03-18T12:00:00Z",
                        },
                        "meta": {
                            "cached": None,
                            "cached_at": None,
                            "stale": None,
                            "source_status": None,
                        },
                    },
                    {
                        "error": {
                            "code": "invalid_vat_format",
                            "message": "Invalid VAT format",
                        },
                        "meta": {"vat_number": "XX000000000"},
                    },
                ],
                "summary": {"total": 2, "succeeded": 1, "failed": 1},
            },
            "meta": {
                "request_id": "req_batch_mixed",
                "mode": None,
                "request_duration_ms": 200,
            },
        }
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=mixed, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate_batch(["NL123456789B01", "XX000000000"])
        assert len(result.results) == 2
        assert result.summary.succeeded == 1
        assert result.summary.failed == 1
        assert is_batch_success(result.results[0]) is True
        assert is_batch_success(result.results[1]) is False
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_all_fail_batch(self, respx_mock: respx.MockRouter) -> None:
        all_fail = {
            "data": {
                "results": [
                    {
                        "error": {"code": "invalid_vat_format", "message": "Invalid"},
                        "meta": {"vat_number": "XX1"},
                    },
                    {
                        "error": {"code": "invalid_vat_format", "message": "Invalid"},
                        "meta": {"vat_number": "XX2"},
                    },
                ],
                "summary": {"total": 2, "succeeded": 0, "failed": 2},
            },
            "meta": {
                "request_id": "req_all_fail",
                "mode": None,
                "request_duration_ms": 50,
            },
        }
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=all_fail, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate_batch(["XX1", "XX2"])
        assert result.summary.failed == 2
        assert all(not is_batch_success(r) for r in result.results)
        client.close()


class TestBatchRequestParams:
    @respx.mock(base_url=BASE_URL)
    def test_sends_requester_vat_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate_batch(["NL123456789B01"], requester_vat_number="DE987654321")
        body = json.loads(route.calls[0].request.content)
        assert body["requester_vat_number"] == "DE987654321"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_cache_false(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate_batch(["NL123456789B01"], cache=False)
        body = json.loads(route.calls[0].request.content)
        assert body["cache"] is False
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_sends_request_id_header(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate_batch(["NL123456789B01"], request_id="batch-trace-123")
        assert route.calls[0].request.headers["x-request-id"] == "batch-trace-123"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_trims_vat_numbers(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate_batch(["  NL123456789B01  ", " DE987654321 "])
        body = json.loads(route.calls[0].request.content)
        assert body["vat_numbers"] == ["NL123456789B01", "DE987654321"]
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit_headers(self, respx_mock: respx.MockRouter) -> None:
        headers = {
            "x-ratelimit-limit": "50",
            "x-ratelimit-remaining": "48",
            "x-ratelimit-reset": "2026-05-01T00:00:00Z",
        }
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=headers)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate_batch(["NL123456789B01"])
        assert result.rate_limit.limit == 50
        assert result.rate_limit.remaining == 48
        client.close()


class TestBatchPerItemMeta:
    @respx.mock(base_url=BASE_URL)
    def test_source_status_on_item(self, respx_mock: respx.MockRouter) -> None:
        resp = {
            "data": {
                "results": [
                    {
                        "data": {
                            "valid": True,
                            "vat_number": "NL123456789B01",
                            "country_code": "NL",
                            "company": {"name": "Test BV", "address": "Amsterdam"},
                            "consultation_number": None,
                            "requested_at": "2026-03-18T12:00:00Z",
                        },
                        "meta": {
                            "cached": None,
                            "cached_at": None,
                            "stale": None,
                            "source_status": "live",
                        },
                    },
                ],
                "summary": {"total": 1, "succeeded": 1, "failed": 0},
            },
            "meta": {
                "request_id": "req_batch_ss",
                "mode": None,
                "request_duration_ms": 100,
            },
        }
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=resp, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        result = client.vat.validate_batch(["NL123456789B01"])
        item = result.results[0]
        assert is_batch_success(item)
        from avatcado import BatchResultSuccess

        assert isinstance(item, BatchResultSuccess)
        assert item.meta.source_status == "live"
        client.close()


class TestBatchClientSideErrors:
    def test_empty_list(self) -> None:
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate_batch([])
        assert exc_info.value.code == "missing_parameter"
        client.close()

    def test_exceeds_50(self) -> None:
        client = Avatcado(MOCK_API_KEY)
        vat_numbers = [f"NL{str(i).zfill(9)}B01" for i in range(51)]
        with pytest.raises(ValidationError) as exc_info:
            client.vat.validate_batch(vat_numbers)
        assert exc_info.value.code == "batch_too_large"
        assert "50" in exc_info.value.message
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_50_items_accepted(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        vat_numbers = [f"NL{str(i).zfill(9)}B01" for i in range(50)]
        result = client.vat.validate_batch(vat_numbers)
        assert result is not None
        client.close()


class TestBatchApiErrors:
    @respx.mock(base_url=BASE_URL)
    def test_tier_insufficient(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {"message": "Upgrade your plan", "code": "tier_insufficient"},
                    "meta": {"request_id": "req_batch_tier"},
                },
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AuthenticationError) as exc_info:
            client.vat.validate_batch(["NL123456789B01"])
        assert exc_info.value.code == "tier_insufficient"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_rate_limit(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {
                        "message": "Rate limit exceeded",
                        "code": "rate_limit_exceeded",
                    },
                    "meta": {"request_id": "req_batch_rl"},
                },
                headers={"retry-after": "15"},
            )
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(RateLimitError) as exc_info:
            client.vat.validate_batch(["NL123456789B01"])
        assert exc_info.value.retry_after == 15.0
        client.close()


class TestBatchNetworkErrors:
    @respx.mock(base_url=BASE_URL)
    def test_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(side_effect=httpx.ReadTimeout("timed out"))
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate_batch(["NL123456789B01"])
        assert exc_info.value.code == "timeout"
        assert exc_info.value.status_code == 0
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_connection_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate_batch(["NL123456789B01"])
        assert exc_info.value.code == "network_error"
        client.close()

    @respx.mock(base_url=BASE_URL)
    def test_non_json_502(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(502, text="<html>Bad Gateway</html>")
        )
        client = Avatcado(MOCK_API_KEY)
        with pytest.raises(AvatcadoError) as exc_info:
            client.vat.validate_batch(["NL123456789B01"])
        assert exc_info.value.code == "unknown_error"
        assert exc_info.value.status_code == 502
        client.close()


class TestBatchContentType:
    @respx.mock(base_url=BASE_URL)
    def test_sends_json_content_type(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            return_value=httpx.Response(200, json=BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        client = Avatcado(MOCK_API_KEY)
        client.vat.validate_batch(["NL123456789B01"])
        content_type = route.calls[0].request.headers["content-type"]
        assert "application/json" in content_type
        client.close()
