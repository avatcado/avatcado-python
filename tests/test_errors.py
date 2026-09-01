from __future__ import annotations

from avatcado import (
    AuthenticationError,
    AvatcadoError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)


class TestAvatcadoError:
    def test_has_correct_properties(self) -> None:
        err = AvatcadoError(
            "test message",
            code="test_code",
            status_code=400,
            request_id="req_123",
            docs_url="https://docs.avatcado.com",
        )
        assert err.message == "test message"
        assert err.code == "test_code"
        assert err.status_code == 400
        assert err.request_id == "req_123"
        assert err.docs_url == "https://docs.avatcado.com"

    def test_str_returns_message(self) -> None:
        err = AvatcadoError("human readable message")
        assert str(err) == "human readable message"

    def test_is_instance_of_exception(self) -> None:
        err = AvatcadoError("msg")
        assert isinstance(err, Exception)

    def test_request_id_defaults_to_none(self) -> None:
        err = AvatcadoError("msg")
        assert err.request_id is None

    def test_docs_url_defaults_to_empty(self) -> None:
        err = AvatcadoError("msg")
        assert err.docs_url == ""

    def test_details_defaults_to_none(self) -> None:
        err = AvatcadoError("msg")
        assert err.details is None

    def test_details_carries_array(self) -> None:
        details = [{"field": "vat_number", "message": "is required"}]
        err = AvatcadoError("msg", details=details)
        assert err.details == [{"field": "vat_number", "message": "is required"}]


class TestErrorHierarchy:
    def test_authentication_error_isinstance(self) -> None:
        err = AuthenticationError("msg", code="unauthorized", status_code=401)
        assert isinstance(err, AvatcadoError)
        assert isinstance(err, AuthenticationError)

    def test_validation_error_isinstance(self) -> None:
        err = ValidationError("msg", code="invalid_vat_format", status_code=422)
        assert isinstance(err, AvatcadoError)
        assert isinstance(err, ValidationError)

    def test_rate_limit_error_isinstance(self) -> None:
        err = RateLimitError("msg", code="rate_limit_exceeded", status_code=429, retry_after=30.0)
        assert isinstance(err, AvatcadoError)
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 30.0

    def test_upstream_error_isinstance(self) -> None:
        err = UpstreamError("msg", code="upstream_unavailable", status_code=503, retry_after=60.0)
        assert isinstance(err, AvatcadoError)
        assert isinstance(err, UpstreamError)
        assert err.retry_after == 60.0

    def test_authentication_error_has_no_details(self) -> None:
        err = AuthenticationError("msg", code="unauthorized", status_code=401)
        assert err.details is None

    def test_rate_limit_error_retry_after_none(self) -> None:
        err = RateLimitError("msg", code="rate_limit_exceeded", status_code=429)
        assert err.retry_after is None

    def test_upstream_error_retry_after_none(self) -> None:
        err = UpstreamError("msg", code="upstream_unavailable", status_code=503)
        assert err.retry_after is None


class TestErrorRequestContext:
    def test_base_request_context_defaults_to_none(self) -> None:
        err = AvatcadoError("msg")
        assert err.vat_number is None
        assert err.requester_vat_number is None

    def test_base_carries_request_context(self) -> None:
        err = AvatcadoError(
            "msg",
            code="internal_error",
            status_code=500,
            vat_number="SE556677889901",
            requester_vat_number="NL861234567B01",
        )
        assert err.vat_number == "SE556677889901"
        assert err.requester_vat_number == "NL861234567B01"

    def test_base_positional_construction_unchanged(self) -> None:
        details = [{"field": "vat_number", "message": "is required"}]
        err = AvatcadoError("msg", "validation_error", 422, "req_1", "https://d", details)
        assert err.code == "validation_error"
        assert err.status_code == 422
        assert err.request_id == "req_1"
        assert err.docs_url == "https://d"
        assert err.details == details
        assert err.vat_number is None
        assert err.requester_vat_number is None

    def test_authentication_error_request_context_defaults_to_none(self) -> None:
        err = AuthenticationError("msg", code="unauthorized", status_code=401)
        assert err.vat_number is None
        assert err.requester_vat_number is None

    def test_validation_error_carries_request_context(self) -> None:
        err = ValidationError(
            "msg", code="invalid_vat_format", status_code=422, vat_number="XX000"
        )
        assert err.vat_number == "XX000"
        assert err.requester_vat_number is None

    def test_validation_error_positional_details_unchanged(self) -> None:
        details = [{"field": "x", "message": "y"}]
        err = ValidationError("msg", "validation_error", 422, "req", "https://d", details)
        assert err.details == details
        assert err.vat_number is None

    def test_rate_limit_error_carries_request_context_and_retry_after(self) -> None:
        err = RateLimitError(
            "msg",
            code="rate_limit_exceeded",
            status_code=429,
            retry_after=30.0,
            vat_number="SE556677889901",
            requester_vat_number="NL861234567B01",
        )
        assert err.retry_after == 30.0
        assert err.vat_number == "SE556677889901"
        assert err.requester_vat_number == "NL861234567B01"

    def test_rate_limit_positional_retry_after_unchanged(self) -> None:
        err = RateLimitError("msg", "rate_limit_exceeded", 429, "req", "", 30.0)
        assert err.retry_after == 30.0
        assert err.vat_number is None

    def test_upstream_error_validation_id_defaults_to_none(self) -> None:
        err = UpstreamError("msg", code="upstream_unavailable", status_code=503)
        assert err.validation_id is None
        assert err.vat_number is None
        assert err.requester_vat_number is None

    def test_upstream_error_carries_full_context(self) -> None:
        err = UpstreamError(
            "msg",
            code="upstream_unavailable",
            status_code=503,
            retry_after=60.0,
            vat_number="SE556677889901",
            requester_vat_number="NL861234567B01",
            validation_id="7c9e6679-7425-40de-944b-e07fc1f90ae7",
        )
        assert err.retry_after == 60.0
        assert err.vat_number == "SE556677889901"
        assert err.requester_vat_number == "NL861234567B01"
        assert err.validation_id == "7c9e6679-7425-40de-944b-e07fc1f90ae7"

    def test_upstream_positional_retry_after_unchanged(self) -> None:
        err = UpstreamError("msg", "upstream_unavailable", 503, "req", "", 60.0)
        assert err.retry_after == 60.0
        assert err.validation_id is None
