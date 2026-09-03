from __future__ import annotations

from typing import get_args

import pytest

from avatcado import (
    AvatcadoError,
    BatchErrorDetail,
    BatchErrorMeta,
    BatchItemMeta,
    BatchResultError,
    BatchResultSuccess,
    BatchSummary,
    Company,
    ResponseMeta,
    SourceStatus,
    VatRate,
    VatValidationResult,
    is_batch_success,
)


class TestCompany:
    def test_from_dict(self) -> None:
        c = Company.from_dict({"name": "Test BV", "address": "Amsterdam"})
        assert c.name == "Test BV"
        assert c.address == "Amsterdam"

    def test_from_dict_null_address(self) -> None:
        c = Company.from_dict({"name": "Test BV", "address": None})
        assert c.address is None


class TestVatValidationResult:
    def test_from_dict_with_company(self) -> None:
        r = VatValidationResult.from_dict(
            {
                "valid": True,
                "vat_number": "NL123456789B01",
                "country_code": "NL",
                "company": {"name": "Test BV", "address": "Amsterdam"},
                "consultation_number": "WAPI123",
                "requested_at": "2026-03-18T12:00:00Z",
            }
        )
        assert r.valid is True
        assert r.vat_number == "NL123456789B01"
        assert r.company is not None
        assert r.company.name == "Test BV"
        assert r.consultation_number == "WAPI123"

    def test_from_dict_null_company(self) -> None:
        r = VatValidationResult.from_dict(
            {
                "valid": False,
                "vat_number": "XX000",
                "country_code": "XX",
                "company": None,
                "consultation_number": None,
                "requested_at": "2026-03-18T12:00:00Z",
            }
        )
        assert r.company is None
        assert r.consultation_number is None


class TestSourceStatus:
    def test_literal_has_five_values(self) -> None:
        assert get_args(SourceStatus) == ("live", "cached", "unavailable", "degraded", "fallback")

    def test_new_values_are_assignable(self) -> None:
        # Type-checked when mypy runs over tests; a narrower Literal rejects these.
        cached: SourceStatus = "cached"
        fallback: SourceStatus = "fallback"
        assert cached == "cached"
        assert fallback == "fallback"


class TestResponseMeta:
    @pytest.mark.parametrize("status", ["cached", "fallback"])
    def test_from_dict_accepts_new_source_statuses(self, status: str) -> None:
        m = ResponseMeta.from_dict({"request_id": "req_1", "source_status": status})
        assert m.source_status == status

    def test_from_dict_full(self) -> None:
        m = ResponseMeta.from_dict(
            {
                "request_id": "req_123",
                "cached": True,
                "cached_at": "2026-03-18T11:00:00Z",
                "stale": False,
                "source": "vies",
                "source_status": "live",
                "mode": "test",
                "request_duration_ms": 150,
            }
        )
        assert m.request_id == "req_123"
        assert m.cached is True
        assert m.stale is False
        assert m.source == "vies"
        assert m.source_status == "live"
        assert m.mode == "test"

    def test_from_dict_minimal(self) -> None:
        m = ResponseMeta.from_dict({"request_id": "req_456"})
        assert m.request_id == "req_456"
        assert m.cached is None
        assert m.source is None
        assert m.source_status is None

    def test_from_dict_null_source_tolerated(self) -> None:
        m = ResponseMeta.from_dict({"request_id": "req_456", "source": None})
        assert m.source is None

    def test_positional_construction_unchanged(self) -> None:
        # The eight pre-0.6 positional parameters keep their order; source is appended.
        m = ResponseMeta("req_1", True, "2026-03-18T11:00:00Z", False, "cached", None, 5, None)
        assert m.request_id == "req_1"
        assert m.count is None
        assert m.source is None
        assert ResponseMeta("req_1", source="anaf").source == "anaf"

    def test_from_dict_with_count(self) -> None:
        m = ResponseMeta.from_dict({"request_id": "req_789", "count": 27})
        assert m.count == 27


class TestBatchTypes:
    def test_batch_result_success_from_dict(self) -> None:
        item = BatchResultSuccess.from_dict(
            {
                "data": {
                    "valid": True,
                    "vat_number": "NL123456789B01",
                    "country_code": "NL",
                    "company": {"name": "Test", "address": None},
                    "consultation_number": None,
                    "requested_at": "2026-03-18T12:00:00Z",
                },
                "meta": {
                    "cached": True,
                    "cached_at": "2026-03-18T11:00:00Z",
                    "stale": False,
                    "source_status": "live",
                },
            }
        )
        assert item.data.valid is True
        assert item.meta.cached is True
        assert item.meta.source_status == "live"

    def test_batch_result_error_from_dict(self) -> None:
        item = BatchResultError.from_dict(
            {
                "error": {"code": "invalid_vat_format", "message": "Invalid"},
                "meta": {"vat_number": "XX000"},
            }
        )
        assert item.error.code == "invalid_vat_format"
        assert item.meta.vat_number == "XX000"

    def test_batch_summary_from_dict(self) -> None:
        s = BatchSummary.from_dict({"total": 3, "succeeded": 2, "failed": 1})
        assert s.total == 3
        assert s.succeeded == 2
        assert s.failed == 1

    def test_batch_result_error_prefers_error_vat_number(self) -> None:
        item = BatchResultError.from_dict(
            {
                "error": {
                    "code": "invalid_vat_format",
                    "message": "Invalid",
                    "vat_number": "XX000",
                },
                "meta": {"vat_number": "XX000"},
            }
        )
        assert item.error.vat_number == "XX000"
        assert item.meta.vat_number == "XX000"

    def test_batch_result_error_falls_back_to_meta_vat_number(self) -> None:
        # Older API responses only carry meta.vat_number
        item = BatchResultError.from_dict(
            {
                "error": {"code": "invalid_vat_format", "message": "Invalid"},
                "meta": {"vat_number": "XX000"},
            }
        )
        assert item.error.vat_number == "XX000"
        assert item.meta.vat_number == "XX000"

    def test_batch_result_error_meta_falls_back_to_error_vat_number(self) -> None:
        # If the deprecated meta.vat_number is ever dropped, meta still resolves
        item = BatchResultError.from_dict(
            {
                "error": {
                    "code": "invalid_vat_format",
                    "message": "Invalid",
                    "vat_number": "XX000",
                },
                "meta": {},
            }
        )
        assert item.error.vat_number == "XX000"
        assert item.meta.vat_number == "XX000"

    def test_batch_result_error_without_any_vat_number_raises_parse_error(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            BatchResultError.from_dict(
                {"error": {"code": "invalid_vat_format", "message": "Invalid"}, "meta": {}}
            )
        assert exc_info.value.code == "parse_error"

    def test_batch_error_detail_constructible_without_vat_number(self) -> None:
        detail = BatchErrorDetail(code="invalid_vat_format", message="Invalid")
        assert detail.vat_number is None


class TestIsBatchSuccess:
    def test_returns_true_for_success(self) -> None:
        item = BatchResultSuccess(
            data=VatValidationResult(
                valid=True,
                vat_number="NL123456789B01",
                country_code="NL",
                company=None,
                consultation_number=None,
                requested_at="2026-03-18T12:00:00Z",
            ),
            meta=BatchItemMeta(cached=None, cached_at=None, stale=None, source_status=None),
        )
        assert is_batch_success(item) is True

    def test_returns_false_for_error(self) -> None:
        item = BatchResultError(
            error=BatchErrorDetail(code="invalid_vat_format", message="Invalid"),
            meta=BatchErrorMeta(vat_number="XX000"),
        )
        assert is_batch_success(item) is False


class TestVatRate:
    def test_from_dict(self) -> None:
        r = VatRate.from_dict(
            {
                "country_code": "NL",
                "country_name": "Netherlands",
                "currency": "EUR",
                "standard_rate": 21,
                "other_rates": [
                    {"rate": 9, "type": "reduced"},
                    {"rate": 0, "type": "zero"},
                ],
                "updated_at": "2026-01-01T00:00:00Z",
            }
        )
        assert r.country_code == "NL"
        assert r.standard_rate == 21
        assert len(r.other_rates) == 2
        assert r.other_rates[0].rate == 9
        assert r.other_rates[0].type == "reduced"


class TestFromDictMissingRequiredField:
    def test_company_missing_name(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            Company.from_dict({})
        assert exc_info.value.code == "parse_error"
        assert "name" in exc_info.value.message

    def test_validation_result_missing_valid(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            VatValidationResult.from_dict({"vat_number": "NL123", "country_code": "NL"})
        assert exc_info.value.code == "parse_error"
        assert "valid" in exc_info.value.message

    def test_response_meta_missing_request_id(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            ResponseMeta.from_dict({})
        assert exc_info.value.code == "parse_error"
        assert "request_id" in exc_info.value.message

    def test_batch_summary_missing_total(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            BatchSummary.from_dict({"succeeded": 1, "failed": 0})
        assert exc_info.value.code == "parse_error"
        assert "total" in exc_info.value.message

    def test_vat_rate_missing_country_code(self) -> None:
        with pytest.raises(AvatcadoError) as exc_info:
            VatRate.from_dict({"country_name": "NL", "currency": "EUR"})
        assert exc_info.value.code == "parse_error"


class TestFromDictExtraFields:
    def test_validation_result_ignores_extra_fields(self) -> None:
        r = VatValidationResult.from_dict(
            {
                "valid": True,
                "vat_number": "NL123456789B01",
                "country_code": "NL",
                "company": None,
                "consultation_number": None,
                "requested_at": "2026-03-18T12:00:00Z",
                "future_field": "ignored",
            }
        )
        assert r.valid is True

    def test_response_meta_ignores_extra_fields(self) -> None:
        m = ResponseMeta.from_dict({"request_id": "req_123", "new_feature": True, "extra": 42})
        assert m.request_id == "req_123"

    def test_company_ignores_extra_fields(self) -> None:
        c = Company.from_dict({"name": "Test BV", "address": "NL", "extra": "ignored"})
        assert c.name == "Test BV"
