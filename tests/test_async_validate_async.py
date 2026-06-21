from __future__ import annotations

import json

import httpx
import pytest
import respx

from avatcado import (
    AsyncAvatcado,
    AsyncBatchValidateResponse,
    AsyncValidateResponse,
)
from avatcado._errors import AuthenticationError, AvatcadoError, ValidationError
from tests.conftest import (
    ASYNC_BATCH_RESPONSE,
    ASYNC_SINGLE_RESPONSE,
    BASE_URL,
    MOCK_API_KEY,
    RATE_LIMIT_HEADERS,
)


class TestAsyncValidateSuccess:
    @respx.mock(base_url=BASE_URL)
    async def test_returns_async_validate_response(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate("DE123456789")
            assert isinstance(result, AsyncValidateResponse)
            assert result.data.request_id == "550e8400-e29b-41d4-a716-446655440000"
            assert result.data.status == "pending"
            assert result.data.vat_number == "DE123456789"

    @respx.mock(base_url=BASE_URL)
    async def test_sends_post_to_correct_endpoint(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("DE123456789")
            body = json.loads(route.calls[0].request.content)
            assert body["vat_number"] == "DE123456789"

    @respx.mock(base_url=BASE_URL)
    async def test_sends_requester_vat_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("DE123456789", requester_vat_number="NL987654321B01")
            body = json.loads(route.calls[0].request.content)
            assert body["requester_vat_number"] == "NL987654321B01"

    @respx.mock(base_url=BASE_URL)
    async def test_sends_cache_false(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("DE123456789", cache=False)
            body = json.loads(route.calls[0].request.content)
            assert body["cache"] is False

    @respx.mock(base_url=BASE_URL)
    async def test_does_not_send_cache_when_true(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("DE123456789")
            body = json.loads(route.calls[0].request.content)
            assert "cache" not in body

    @respx.mock(base_url=BASE_URL)
    async def test_parses_meta(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate("DE123456789")
            assert result.meta.request_id == "req_async1"

    @respx.mock(base_url=BASE_URL)
    async def test_parses_rate_limit_headers(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate("DE123456789")
            assert result.rate_limit.limit == 100
            assert result.rate_limit.remaining == 99

    @respx.mock(base_url=BASE_URL)
    async def test_trims_whitespace(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("  DE123456789  ")
            body = json.loads(route.calls[0].request.content)
            assert body["vat_number"] == "DE123456789"

    @respx.mock(base_url=BASE_URL)
    async def test_sends_request_id_header(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                202, json=ASYNC_SINGLE_RESPONSE, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate("DE123456789", request_id="trace-123")
            assert route.calls[0].request.headers["x-request-id"] == "trace-123"


class TestAsyncValidateErrors:
    async def test_empty_vat_number(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError, match="vat_number is required") as exc_info:
                await client.async_vat.validate("")
            assert exc_info.value.code == "missing_parameter"

    async def test_whitespace_only_vat_number(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError, match="vat_number is required"):
                await client.async_vat.validate("   ")

    @respx.mock(base_url=BASE_URL)
    async def test_tier_insufficient(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {"code": "tier_insufficient", "message": "Upgrade to Pro"},
                    "meta": {"request_id": "req_err1"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.async_vat.validate("DE123456789")
            assert exc_info.value.code == "tier_insufficient"
            assert exc_info.value.status_code == 403

    @respx.mock(base_url=BASE_URL)
    async def test_webhook_not_configured(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {"code": "webhook_not_configured", "message": "No webhook URL"},
                    "meta": {"request_id": "req_err2"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.async_vat.validate("DE123456789")
            assert exc_info.value.code == "webhook_not_configured"

    @respx.mock(base_url=BASE_URL)
    async def test_timeout(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(side_effect=httpx.ReadTimeout("timed out"))
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.async_vat.validate("DE123456789")
            assert exc_info.value.code == "timeout"

    @respx.mock(base_url=BASE_URL)
    async def test_network_error(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.async_vat.validate("DE123456789")
            assert exc_info.value.code == "network_error"


class TestAsyncValidateBatchSuccess:
    @respx.mock(base_url=BASE_URL)
    async def test_returns_batch_response(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate_batch(["DE123456789", "NL987654321B01"])
            assert isinstance(result, AsyncBatchValidateResponse)
            assert result.data.batch_id == "660e8400-e29b-41d4-a716-446655440000"
            assert result.data.status == "pending"
            assert result.data.total == 2
            assert result.data.accepted == 2

    @respx.mock(base_url=BASE_URL)
    async def test_sends_post_to_correct_endpoint(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate_batch(["DE123456789", "NL987654321B01"])
            body = json.loads(route.calls[0].request.content)
            assert body["vat_numbers"] == ["DE123456789", "NL987654321B01"]

    @respx.mock(base_url=BASE_URL)
    async def test_handles_rejected_items(self, respx_mock: respx.MockRouter) -> None:
        response_with_rejected = {
            "data": {
                "batch_id": "770e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "total": 3,
                "accepted": 2,
                "rejected": [
                    {
                        "vat_number": "XX000",
                        "error": {"code": "invalid_vat_format", "message": "Invalid format"},
                    }
                ],
            },
            "meta": {"request_id": "req_async_batch2"},
        }
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(
                202, json=response_with_rejected, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate_batch(
                ["DE123456789", "NL987654321B01", "XX000"]
            )
            assert len(result.data.rejected) == 1
            assert result.data.rejected[0].vat_number == "XX000"
            assert result.data.rejected[0].error_code == "invalid_vat_format"
            assert result.data.rejected[0].error_message == "Invalid format"

    @respx.mock(base_url=BASE_URL)
    async def test_handles_all_rejected(self, respx_mock: respx.MockRouter) -> None:
        all_rejected_response = {
            "data": {
                "batch_id": None,
                "status": "completed",
                "total": 2,
                "accepted": 0,
                "rejected": [
                    {
                        "vat_number": "XX000",
                        "error": {"code": "invalid_vat_format", "message": "Invalid format"},
                    },
                    {
                        "vat_number": "YY111",
                        "error": {"code": "invalid_vat_format", "message": "Invalid format"},
                    },
                ],
            },
            "meta": {"request_id": "req_async_batch3"},
        }
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(
                202, json=all_rejected_response, headers=RATE_LIMIT_HEADERS
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate_batch(["XX000", "YY111"])
            assert result.data.batch_id is None
            assert result.data.status == "completed"
            assert result.data.accepted == 0
            assert len(result.data.rejected) == 2

    @respx.mock(base_url=BASE_URL)
    async def test_sends_requester_vat_number(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate_batch(
                ["DE123456789"], requester_vat_number="NL987654321B01"
            )
            body = json.loads(route.calls[0].request.content)
            assert body["requester_vat_number"] == "NL987654321B01"

    @respx.mock(base_url=BASE_URL)
    async def test_sends_cache_false(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate_batch(["DE123456789"], cache=False)
            body = json.loads(route.calls[0].request.content)
            assert body["cache"] is False

    @respx.mock(base_url=BASE_URL)
    async def test_parses_rate_limit_headers(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            result = await client.async_vat.validate_batch(["DE123456789"])
            assert result.rate_limit.limit == 100
            assert result.rate_limit.remaining == 99

    @respx.mock(base_url=BASE_URL)
    async def test_trims_whitespace(self, respx_mock: respx.MockRouter) -> None:
        route = respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=ASYNC_BATCH_RESPONSE, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            await client.async_vat.validate_batch(["  DE123456789  ", "  NL987654321B01  "])
            body = json.loads(route.calls[0].request.content)
            assert body["vat_numbers"] == ["DE123456789", "NL987654321B01"]

    @respx.mock(base_url=BASE_URL)
    async def test_no_max_batch_size_enforced(self, respx_mock: respx.MockRouter) -> None:
        large_batch_response = {
            "data": {
                "batch_id": "880e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "total": 200,
                "accepted": 200,
                "rejected": [],
            },
            "meta": {"request_id": "req_async_batch_large"},
        }
        route = respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(202, json=large_batch_response, headers=RATE_LIMIT_HEADERS)
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            vat_numbers = [f"DE{str(i).zfill(9)}" for i in range(200)]
            result = await client.async_vat.validate_batch(vat_numbers)
            assert result.data.total == 200
            body = json.loads(route.calls[0].request.content)
            assert len(body["vat_numbers"]) == 200


class TestAsyncValidateBatchErrors:
    async def test_empty_list(self) -> None:
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(ValidationError, match="At least one VAT number is required"):
                await client.async_vat.validate_batch([])

    @respx.mock(base_url=BASE_URL)
    async def test_tier_insufficient(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(
                403,
                json={
                    "error": {"code": "tier_insufficient", "message": "Upgrade to Pro"},
                    "meta": {"request_id": "req_err3"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.async_vat.validate_batch(["DE123456789"])
            assert exc_info.value.code == "tier_insufficient"

    @respx.mock(base_url=BASE_URL)
    async def test_webhook_not_configured(self, respx_mock: respx.MockRouter) -> None:
        respx_mock.post("/v1/validate/async/batch").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {"code": "webhook_not_configured", "message": "No webhook URL"},
                    "meta": {"request_id": "req_err4"},
                },
            )
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.async_vat.validate_batch(["DE123456789"])
            assert exc_info.value.code == "webhook_not_configured"
