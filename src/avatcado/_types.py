from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


def _require_key(data: Dict[str, Any], key: str, context: str) -> Any:
    try:
        return data[key]
    except KeyError:
        from avatcado._errors import AvatcadoError

        raise AvatcadoError(
            f"Missing required field '{key}' in {context} response",
            code="parse_error",
            status_code=0,
        )


@dataclass
class Company:
    name: str
    address: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Company:
        return cls(
            name=_require_key(data, "name", "Company"),
            address=data.get("address"),
        )


@dataclass
class VatValidationResult:
    valid: bool
    vat_number: str
    country_code: str
    company: Optional[Company]
    consultation_number: Optional[str]
    requested_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VatValidationResult:
        company_data = data.get("company")
        company = Company.from_dict(company_data) if company_data is not None else None
        return cls(
            valid=_require_key(data, "valid", "VatValidationResult"),
            vat_number=_require_key(data, "vat_number", "VatValidationResult"),
            country_code=_require_key(data, "country_code", "VatValidationResult"),
            company=company,
            consultation_number=data.get("consultation_number"),
            requested_at=_require_key(data, "requested_at", "VatValidationResult"),
        )


SourceStatus = Literal["live", "unavailable", "degraded"]


@dataclass
class ResponseMeta:
    request_id: str
    cached: Optional[bool] = None
    cached_at: Optional[str] = None
    stale: Optional[bool] = None
    source_status: Optional[SourceStatus] = None
    mode: Optional[Literal["test"]] = None
    request_duration_ms: Optional[int] = None
    count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResponseMeta:
        return cls(
            request_id=_require_key(data, "request_id", "ResponseMeta"),
            cached=data.get("cached"),
            cached_at=data.get("cached_at"),
            stale=data.get("stale"),
            source_status=data.get("source_status"),
            mode=data.get("mode"),
            request_duration_ms=data.get("request_duration_ms"),
            count=data.get("count"),
        )


@dataclass
class RateLimitInfo:
    limit: Optional[int]
    remaining: Optional[int]
    reset: Optional[str]
    retry_after: Optional[float]
    burst_limit: Optional[int]
    burst_remaining: Optional[int]


@dataclass
class ValidateResponse:
    data: VatValidationResult
    meta: ResponseMeta
    rate_limit: RateLimitInfo


@dataclass
class BatchItemMeta:
    cached: Optional[bool]
    cached_at: Optional[str]
    stale: Optional[bool]
    source_status: Optional[SourceStatus]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatchItemMeta:
        return cls(
            cached=data.get("cached"),
            cached_at=data.get("cached_at"),
            stale=data.get("stale"),
            source_status=data.get("source_status"),
        )


@dataclass
class BatchErrorDetail:
    code: str
    message: str


@dataclass
class BatchErrorMeta:
    vat_number: str


@dataclass
class BatchResultSuccess:
    data: VatValidationResult
    meta: BatchItemMeta

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatchResultSuccess:
        return cls(
            data=VatValidationResult.from_dict(data["data"]),
            meta=BatchItemMeta.from_dict(data["meta"]),
        )


@dataclass
class BatchResultError:
    error: BatchErrorDetail
    meta: BatchErrorMeta

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatchResultError:
        error_data = _require_key(data, "error", "BatchResultError")
        meta_data = _require_key(data, "meta", "BatchResultError")
        return cls(
            error=BatchErrorDetail(
                code=_require_key(error_data, "code", "BatchErrorDetail"),
                message=_require_key(error_data, "message", "BatchErrorDetail"),
            ),
            meta=BatchErrorMeta(
                vat_number=_require_key(meta_data, "vat_number", "BatchErrorMeta"),
            ),
        )


BatchResult = Union[BatchResultSuccess, BatchResultError]


def is_batch_success(item: BatchResult) -> TypeGuard[BatchResultSuccess]:
    """Type guard to check if a batch result item is a success."""
    return isinstance(item, BatchResultSuccess)


@dataclass
class BatchSummary:
    total: int
    succeeded: int
    failed: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatchSummary:
        return cls(
            total=_require_key(data, "total", "BatchSummary"),
            succeeded=_require_key(data, "succeeded", "BatchSummary"),
            failed=_require_key(data, "failed", "BatchSummary"),
        )


@dataclass
class BatchValidateResponse:
    results: List[BatchResult]
    summary: BatchSummary
    meta: ResponseMeta
    rate_limit: RateLimitInfo


@dataclass
class OtherRate:
    rate: float
    type: str


@dataclass
class VatRate:
    country_code: str
    country_name: str
    currency: str
    standard_rate: float
    other_rates: List[OtherRate]
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VatRate:
        other_rates = [
            OtherRate(
                rate=_require_key(r, "rate", "OtherRate"),
                type=_require_key(r, "type", "OtherRate"),
            )
            for r in _require_key(data, "other_rates", "VatRate")
        ]
        return cls(
            country_code=_require_key(data, "country_code", "VatRate"),
            country_name=_require_key(data, "country_name", "VatRate"),
            currency=_require_key(data, "currency", "VatRate"),
            standard_rate=_require_key(data, "standard_rate", "VatRate"),
            other_rates=other_rates,
            updated_at=_require_key(data, "updated_at", "VatRate"),
        )


@dataclass
class ListRatesResponse:
    data: List[VatRate]
    meta: ResponseMeta
    rate_limit: RateLimitInfo


@dataclass
class GetRateResponse:
    data: VatRate
    meta: ResponseMeta
    rate_limit: RateLimitInfo


@dataclass
class AsyncValidateData:
    request_id: str
    status: str
    vat_number: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AsyncValidateData:
        return cls(
            request_id=_require_key(data, "request_id", "AsyncValidateData"),
            status=_require_key(data, "status", "AsyncValidateData"),
            vat_number=_require_key(data, "vat_number", "AsyncValidateData"),
        )


@dataclass
class AsyncMeta:
    request_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AsyncMeta:
        return cls(
            request_id=_require_key(data, "request_id", "AsyncMeta"),
        )


@dataclass
class AsyncValidateResponse:
    data: AsyncValidateData
    meta: AsyncMeta
    rate_limit: RateLimitInfo


@dataclass
class AsyncBatchRejectedItem:
    vat_number: str
    error_code: str
    error_message: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AsyncBatchRejectedItem:
        error_data = _require_key(data, "error", "AsyncBatchRejectedItem")
        return cls(
            vat_number=_require_key(data, "vat_number", "AsyncBatchRejectedItem"),
            error_code=_require_key(error_data, "code", "AsyncBatchRejectedItem.error"),
            error_message=_require_key(error_data, "message", "AsyncBatchRejectedItem.error"),
        )


@dataclass
class AsyncBatchData:
    batch_id: Optional[str]
    status: str
    total: int
    accepted: int
    rejected: List[AsyncBatchRejectedItem]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AsyncBatchData:
        rejected_raw = _require_key(data, "rejected", "AsyncBatchData")
        return cls(
            batch_id=data.get("batch_id"),
            status=_require_key(data, "status", "AsyncBatchData"),
            total=_require_key(data, "total", "AsyncBatchData"),
            accepted=_require_key(data, "accepted", "AsyncBatchData"),
            rejected=[AsyncBatchRejectedItem.from_dict(r) for r in rejected_raw],
        )


@dataclass
class AsyncBatchValidateResponse:
    data: AsyncBatchData
    meta: AsyncMeta
    rate_limit: RateLimitInfo
