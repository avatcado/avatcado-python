from __future__ import annotations

from typing import Any, Dict, List, Union

import httpx
import pytest
import respx

from avatcado import AsyncAvatcado, Avatcado, AvatcadoError, RateLimitError, UpstreamError
from tests.conftest import BASE_URL, MOCK_API_KEY

OK_VALIDATE: Dict[str, Any] = {
    "data": {
        "valid": True,
        "vat_number": "DE123456789",
        "country_code": "DE",
        "company": None,
        "requested_at": "2026-11-16T12:00:00Z",
    },
    "meta": {
        "request_id": "req_ok",
        "source": "vies",
        "source_status": "live",
        "cached": False,
        "stale": False,
    },
}
OK_ASYNC: Dict[str, Any] = {
    "data": {"request_id": "async_1", "status": "pending", "vat_number": "DE123456789"},
    "meta": {"request_id": "req_ok"},
}

Outcome = Union[httpx.Response, Exception]


def ok(body: Dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=body)


def api_error(status: int, code: str, retry_after: Union[str, None] = None) -> httpx.Response:
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    return httpx.Response(
        status,
        json={"error": {"code": code, "message": code}, "meta": {"request_id": "req_err"}},
        headers=headers,
    )


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """Replaces the SDK's sleep functions and records every wait, so no test really waits."""
    recorded: List[float] = []

    def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    async def fake_async_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr("avatcado._base_client._sleep", fake_sleep)
    monkeypatch.setattr("avatcado._base_client._async_sleep", fake_async_sleep)
    return recorded


class TestRetriesOffByDefault:
    @respx.mock(base_url=BASE_URL)
    def test_first_failure_is_returned(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(429, "burst_limit_exceeded", "1"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY) as client, pytest.raises(RateLimitError):
            client.vat.validate("DE123456789")

        assert route.call_count == 1
        assert sleeps == []


class TestMaxRetries:
    @respx.mock(base_url=BASE_URL)
    def test_burst_429_waits_retry_after_then_succeeds(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(429, "burst_limit_exceeded", "3"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=2) as client:
            result = client.vat.validate("DE123456789")

        assert result.data.valid is True
        assert route.call_count == 2
        assert sleeps == [3.0]

    @respx.mock(base_url=BASE_URL)
    def test_monthly_quota_429_is_not_retried(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(429, "rate_limit_exceeded", "5"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=3) as client, pytest.raises(RateLimitError):
            client.vat.validate("DE123456789")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL)
    def test_503_with_short_retry_after_is_retried(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(503, "internal_error", "5"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=1) as client:
            client.vat.validate("DE123456789")

        assert route.call_count == 2
        assert sleeps == [5.0]

    @respx.mock(base_url=BASE_URL)
    def test_retry_after_above_the_cap_returns_at_once(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(503, "upstream_unavailable", "300"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=3) as client:
            with pytest.raises(UpstreamError) as exc_info:
                client.vat.validate("DE123456789")

        assert exc_info.value.retry_after == 300
        assert route.call_count == 1
        assert sleeps == []

    @respx.mock(base_url=BASE_URL)
    def test_custom_max_retry_delay_in_seconds(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(503, "upstream_unavailable", "300"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=1, max_retry_delay=300) as client:
            client.vat.validate("DE123456789")

        assert route.call_count == 2
        assert sleeps == [300.0]

    @respx.mock(base_url=BASE_URL)
    def test_stops_after_max_retries(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=api_error(429, "burst_limit_exceeded", "1")
        )
        with Avatcado(MOCK_API_KEY, max_retries=2) as client:
            with pytest.raises(RateLimitError) as exc_info:
                client.vat.validate("DE123456789")

        assert exc_info.value.code == "burst_limit_exceeded"
        assert route.call_count == 3
        assert sleeps == [1.0, 1.0]

    @respx.mock(base_url=BASE_URL)
    def test_get_retries_network_errors_and_timeouts_with_backoff(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        outcomes: List[Outcome] = [
            httpx.ConnectError("refused"),
            httpx.ReadTimeout("timed out"),
            ok(OK_VALIDATE),
        ]
        route = respx_mock.get("/v1/validate").mock(side_effect=outcomes)
        with Avatcado(MOCK_API_KEY, max_retries=2) as client:
            client.vat.validate("DE123456789")

        assert route.call_count == 3
        assert len(sleeps) == 2
        assert 0.25 <= sleeps[0] <= 0.5
        assert 0.5 <= sleeps[1] <= 1.0

    @respx.mock(base_url=BASE_URL)
    def test_backoff_never_exceeds_eight_seconds(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        respx_mock.get("/v1/rates").mock(side_effect=httpx.ConnectError("refused"))
        with Avatcado(MOCK_API_KEY, max_retries=8) as client, pytest.raises(AvatcadoError):
            client.rates.list()

        assert len(sleeps) == 8
        assert max(sleeps) <= 8.0

    @respx.mock(base_url=BASE_URL)
    def test_get_retries_502_and_504(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[
                httpx.Response(502, text="Bad Gateway"),
                httpx.Response(504, text="Gateway Timeout"),
                ok(OK_VALIDATE),
            ]
        )
        with Avatcado(MOCK_API_KEY, max_retries=2) as client:
            client.vat.validate("DE123456789")

        assert route.call_count == 3

    @pytest.mark.parametrize(
        ("status", "code"),
        [(401, "unauthorized"), (422, "invalid_vat_format"), (500, "internal_error")],
    )
    @respx.mock(base_url=BASE_URL)
    def test_4xx_and_500_are_not_retried(
        self, respx_mock: respx.MockRouter, sleeps: List[float], status: int, code: str
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(status, code), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=3) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                client.vat.validate("DE123456789")

        assert exc_info.value.code == code
        assert route.call_count == 1

    # A POST that timed out or lost its connection may have been accepted: retrying could
    # queue the same validation twice.
    @pytest.mark.parametrize(
        "failure",
        [
            httpx.ReadTimeout("timed out"),
            httpx.ConnectError("refused"),
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(504, text="Gateway Timeout"),
        ],
        ids=["timeout", "network", "502", "504"],
    )
    @respx.mock(base_url=BASE_URL)
    def test_post_is_not_retried_when_the_outcome_is_unknown(
        self, respx_mock: respx.MockRouter, sleeps: List[float], failure: Outcome
    ) -> None:
        route = respx_mock.post("/v1/validate/async").mock(side_effect=[failure, ok(OK_ASYNC)])
        with Avatcado(MOCK_API_KEY, max_retries=3) as client, pytest.raises(AvatcadoError):
            client.async_vat.validate("DE123456789")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL)
    def test_post_is_retried_when_nothing_was_processed(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.post("/v1/validate/async").mock(
            side_effect=[
                api_error(429, "burst_limit_exceeded", "1"),
                api_error(503, "internal_error", "5"),
                ok(OK_ASYNC),
            ]
        )
        with Avatcado(MOCK_API_KEY, max_retries=2) as client:
            client.async_vat.validate("DE123456789")

        assert route.call_count == 3
        assert sleeps == [1.0, 5.0]

    @respx.mock(base_url=BASE_URL)
    def test_same_request_id_on_every_attempt(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(429, "burst_limit_exceeded", "1"), ok(OK_VALIDATE)]
        )
        with Avatcado(MOCK_API_KEY, max_retries=1) as client:
            client.vat.validate("DE123456789", request_id="trace-7")

        assert [c.request.headers["x-request-id"] for c in route.calls] == ["trace-7", "trace-7"]

    @respx.mock(base_url=BASE_URL)
    def test_negative_max_retries_means_zero(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/validate").mock(
            return_value=api_error(429, "burst_limit_exceeded", "1")
        )
        with Avatcado(MOCK_API_KEY, max_retries=-2) as client, pytest.raises(RateLimitError):
            client.vat.validate("DE123456789")

        assert route.call_count == 1


class TestAsyncClientRetries:
    @respx.mock(base_url=BASE_URL)
    async def test_off_by_default(self, respx_mock: respx.MockRouter, sleeps: List[float]) -> None:
        route = respx_mock.get("/v1/validate").mock(
            side_effect=[api_error(429, "burst_limit_exceeded", "1"), ok(OK_VALIDATE)]
        )
        async with AsyncAvatcado(MOCK_API_KEY) as client:
            with pytest.raises(RateLimitError):
                await client.vat.validate("DE123456789")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL)
    async def test_burst_429_waits_then_succeeds(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.get("/v1/eori/validate").mock(
            side_effect=[
                api_error(429, "burst_limit_exceeded", "2"),
                httpx.ReadTimeout("timed out"),
                httpx.Response(
                    200,
                    json={
                        "data": {
                            "valid": True,
                            "eori_number": "GB123456789000",
                            "country_code": "GB",
                            "company": None,
                            "requested_at": "2026-11-16T12:00:00Z",
                        },
                        "meta": {"request_id": "req_ok"},
                    },
                ),
            ]
        )
        async with AsyncAvatcado(MOCK_API_KEY, max_retries=2) as client:
            result = await client.eori.validate("GB123456789000")

        assert result.data.valid is True
        assert route.call_count == 3
        assert sleeps[0] == 2.0
        assert 0.5 <= sleeps[1] <= 1.0

    @respx.mock(base_url=BASE_URL)
    async def test_post_timeout_is_not_retried(
        self, respx_mock: respx.MockRouter, sleeps: List[float]
    ) -> None:
        route = respx_mock.post("/v1/validate/batch").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        async with AsyncAvatcado(MOCK_API_KEY, max_retries=3) as client:
            with pytest.raises(AvatcadoError) as exc_info:
                await client.vat.validate_batch(["DE123456789"])

        assert exc_info.value.code == "timeout"
        assert route.call_count == 1
