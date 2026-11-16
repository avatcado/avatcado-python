"""Runs the SDK against a real Avatcado API in test mode.

Test keys never reach a register and use no quota, and the magic numbers below give fixed
answers (https://docs.avatcado.com/test-mode).

    AVATCADO_TEST_API_KEY=avat_test_... pytest tests/test_live.py
    AVATCADO_BASE_URL=http://localhost:8787   (optional, for a locally running API)

Skipped when AVATCADO_TEST_API_KEY is not set.
"""

from __future__ import annotations

import os
from typing import Optional

import pytest

from avatcado import (
    AsyncAvatcado,
    AuthenticationError,
    Avatcado,
    AvatcadoError,
    RateLimitError,
    UpstreamError,
    ValidationError,
    is_batch_success,
)

KEY = os.environ.get("AVATCADO_TEST_API_KEY", "")
BASE_URL: Optional[str] = os.environ.get("AVATCADO_BASE_URL") or None
REQUESTER = "NL123456789B01"

pytestmark = pytest.mark.skipif(not KEY, reason="AVATCADO_TEST_API_KEY is not set")


def client(api_key: str = KEY) -> Avatcado:
    return Avatcado(api_key, base_url=BASE_URL)


def async_client(api_key: str = KEY) -> AsyncAvatcado:
    return AsyncAvatcado(api_key, base_url=BASE_URL)


def test_runs_with_a_test_key_only() -> None:
    assert KEY.startswith(("avat_test_", "vtly_test_"))


class TestVatValidate:
    def test_valid_number_with_company_and_test_mode_meta(self) -> None:
        with client() as avatcado:
            result = avatcado.vat.validate("de 111.111.111", request_id="sdk-live-1")

        assert result.data.valid is True
        assert result.data.vat_number == "DE111111111"
        assert result.data.country_code == "DE"
        assert result.data.company is not None
        assert result.data.company.name == "Test GmbH"
        assert isinstance(result.data.requested_at, str)
        assert result.meta.request_id == "sdk-live-1"
        assert result.meta.mode == "test"
        # Test keys carry no quota, so the API sends no rate limit headers.
        assert result.rate_limit.limit is None

    def test_invalid_number_has_no_company(self) -> None:
        with client() as avatcado:
            result = avatcado.vat.validate("DE000000000")

        assert result.data.valid is False
        assert result.data.company is None

    def test_valid_number_without_details_has_no_company(self) -> None:
        with client() as avatcado:
            result = avatcado.vat.validate("DE222222222")

        assert result.data.valid is True
        assert result.data.company is None

    def test_malformed_number_raises_validation_error_with_the_number(self) -> None:
        with client() as avatcado, pytest.raises(ValidationError) as exc_info:
            avatcado.vat.validate("DE123")

        error = exc_info.value
        assert error.code == "invalid_vat_format"
        assert error.status_code == 422
        assert error.vat_number == "DE123"
        assert "/errors/invalid_vat_format" in error.docs_url
        assert error.request_id

    def test_register_outage_raises_upstream_error(self) -> None:
        with client() as avatcado, pytest.raises(UpstreamError) as exc_info:
            avatcado.vat.validate("DE999999999")

        assert exc_info.value.code == "upstream_unavailable"
        assert exc_info.value.status_code == 503
        assert exc_info.value.vat_number == "DE999999999"

    def test_quota_and_burst_limits_raise_rate_limit_error(self) -> None:
        with client() as avatcado:
            with pytest.raises(RateLimitError) as quota:
                avatcado.vat.validate("DE777777777")
            with pytest.raises(RateLimitError) as burst:
                avatcado.vat.validate("DE666666666")

        assert quota.value.code == "rate_limit_exceeded"
        assert burst.value.code == "burst_limit_exceeded"

    def test_stored_result_during_an_outage(self) -> None:
        with client() as avatcado:
            result = avatcado.vat.validate("DE555555555")

        assert result.meta.source_status == "unavailable"
        assert result.meta.cached is True
        assert isinstance(result.meta.cached_at, str)

    # With a requester the API serves no stored result unless the request says cache=true.
    # This is the case the SDK could not express before it sent an explicit cache=True.
    def test_requester_gets_503_by_default_and_the_stored_result_with_cache_true(self) -> None:
        with client() as avatcado:
            with pytest.raises(UpstreamError) as exc_info:
                avatcado.vat.validate("DE555555555", requester_vat_number=REQUESTER)
            opted_in = avatcado.vat.validate(
                "DE555555555", requester_vat_number=REQUESTER, cache=True
            )

        assert exc_info.value.code == "upstream_member_state_unavailable"
        assert exc_info.value.requester_vat_number == REQUESTER
        assert opted_in.meta.source_status == "unavailable"

    def test_fallback_false_never_returns_a_register_answer(self) -> None:
        with client() as avatcado, pytest.raises(UpstreamError) as exc_info:
            avatcado.vat.validate("RO555555555", fallback=False)

        assert exc_info.value.code == "upstream_member_state_unavailable"

    def test_default_is_the_register_on_paid_plans_and_a_503_on_free(self) -> None:
        with client() as avatcado:
            try:
                result = avatcado.vat.validate("RO555555555")
            except UpstreamError as error:
                assert error.code == "upstream_member_state_unavailable"
            else:
                assert result.meta.source_status == "fallback"
                assert result.meta.source == "anaf"


class TestVatValidateBatch:
    def test_one_result_per_number_or_tier_insufficient_on_free(self) -> None:
        with client() as avatcado:
            try:
                result = avatcado.vat.validate_batch(["DE111111111", "DE000000000", "DE999999999"])
            except AuthenticationError as error:
                assert error.code == "tier_insufficient"
                return

        assert (result.summary.total, result.summary.succeeded, result.summary.failed) == (3, 2, 1)
        valid, invalid, outage = result.results
        assert is_batch_success(valid) and valid.data.valid is True
        assert is_batch_success(valid) and valid.meta.source == "test"
        assert is_batch_success(invalid) and invalid.data.valid is False
        # A register outage fails that one item; the batch itself still answers 200.
        assert not is_batch_success(outage)
        assert outage.error.code == "upstream_unavailable"
        assert outage.error.vat_number == "DE999999999"


class TestAsyncVat:
    def test_test_keys_are_refused(self) -> None:
        with client() as avatcado, pytest.raises(AuthenticationError) as exc_info:
            avatcado.async_vat.validate("DE111111111")

        assert exc_info.value.code in ("forbidden", "tier_insufficient")


class TestRates:
    def test_list(self) -> None:
        with client() as avatcado:
            result = avatcado.rates.list(request_id="sdk-live-rates")

        assert len(result.data) > 25
        assert result.meta.count == len(result.data)
        assert result.meta.request_id == "sdk-live-rates"
        nl = next(rate for rate in result.data if rate.country_code == "NL")
        assert nl.country_name == "Netherlands"
        assert isinstance(nl.standard_rate, (int, float))
        assert isinstance(nl.other_rates, list)

    def test_get_and_not_found(self) -> None:
        with client() as avatcado:
            found = avatcado.rates.get("nl")
            with pytest.raises(AvatcadoError) as exc_info:
                avatcado.rates.get("ZZ")

        assert found.data.country_code == "NL"
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "not_found"


class TestEoriValidate:
    def test_valid_eu_number_with_trader_details(self) -> None:
        with client() as avatcado:
            result = avatcado.eori.validate("nl 111.111.111")

        assert result.data.valid is True
        assert result.data.eori_number == "NL111111111"
        assert result.data.country_code == "NL"
        assert result.data.company is not None
        assert result.data.company.name == "Test B.V."
        assert result.meta.mode == "test"
        assert result.meta.source == "test"
        assert result.meta.source_status == "live"
        assert result.meta.cached is False

    def test_valid_gb_number(self) -> None:
        with client() as avatcado:
            result = avatcado.eori.validate("GB111111111111")

        assert result.data.valid is True
        assert result.data.country_code == "GB"

    def test_valid_number_without_published_details(self) -> None:
        with client() as avatcado:
            result = avatcado.eori.validate("NL222222222")

        assert result.data.valid is True
        assert result.data.company is None

    def test_number_the_register_does_not_list(self) -> None:
        with client() as avatcado:
            result = avatcado.eori.validate("NL000000000", cache=False)

        assert result.data.valid is False
        assert result.data.company is None

    def test_register_outage_raises_upstream_error_with_the_number(self) -> None:
        with client() as avatcado, pytest.raises(UpstreamError) as exc_info:
            avatcado.eori.validate("NL999999999")

        assert exc_info.value.code == "upstream_unavailable"
        assert exc_info.value.eori_number == "NL999999999"

    def test_malformed_number_raises_validation_error_with_the_number(self) -> None:
        with client() as avatcado, pytest.raises(ValidationError) as exc_info:
            avatcado.eori.validate("GB12")

        assert exc_info.value.code == "invalid_eori_format"
        assert exc_info.value.status_code == 422
        assert exc_info.value.eori_number == "GB12"


class TestAuthentication:
    def test_unknown_key_raises_authentication_error(self) -> None:
        unknown = "avat_test_0000000000000000000000000000000000000000"
        with client(unknown) as avatcado, pytest.raises(AuthenticationError) as exc_info:
            avatcado.rates.list()

        assert exc_info.value.code == "unauthorized"
        assert exc_info.value.status_code == 401


class TestAsyncClient:
    async def test_validate_rates_and_eori(self) -> None:
        async with async_client() as avatcado:
            vat = await avatcado.vat.validate("DE111111111", cache=True, fallback=False)
            rates = await avatcado.rates.get("NL", request_id="sdk-live-async")
            eori = await avatcado.eori.validate("GB111111111111")

        assert vat.data.valid is True
        assert vat.meta.mode == "test"
        assert rates.data.country_code == "NL"
        assert rates.meta.request_id == "sdk-live-async"
        assert eori.data.valid is True

    async def test_errors_are_typed(self) -> None:
        async with async_client() as avatcado:
            with pytest.raises(UpstreamError) as upstream:
                await avatcado.eori.validate("NL999999999")
            with pytest.raises(ValidationError) as invalid:
                await avatcado.vat.validate("DE123")
            with pytest.raises(UpstreamError) as requester:
                await avatcado.vat.validate("DE555555555", requester_vat_number=REQUESTER)
            opted_in = await avatcado.vat.validate(
                "DE555555555", requester_vat_number=REQUESTER, cache=True
            )

        assert upstream.value.eori_number == "NL999999999"
        assert invalid.value.code == "invalid_vat_format"
        assert requester.value.code == "upstream_member_state_unavailable"
        assert opted_in.meta.source_status == "unavailable"
