from __future__ import annotations

from typing import Any, Dict, List, Optional


class AvatcadoError(Exception):
    """Base exception for all Avatcado API errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 0,
        request_id: Optional[str] = None,
        docs_url: str = "",
        details: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.docs_url = docs_url
        self.details = details

    def __str__(self) -> str:
        return self.message


class AuthenticationError(AvatcadoError):
    """Raised for authentication and authorization failures."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 0,
        request_id: Optional[str] = None,
        docs_url: str = "",
    ) -> None:
        super().__init__(message, code, status_code, request_id, docs_url, None)


class ValidationError(AvatcadoError):
    """Raised for request validation failures."""

    pass


class RateLimitError(AvatcadoError):
    """Raised when rate or burst limits are exceeded."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 0,
        request_id: Optional[str] = None,
        docs_url: str = "",
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, code, status_code, request_id, docs_url, None)
        self.retry_after = retry_after


class UpstreamError(AvatcadoError):
    """Raised when an upstream tax authority is unavailable."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 0,
        request_id: Optional[str] = None,
        docs_url: str = "",
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, code, status_code, request_id, docs_url, None)
        self.retry_after = retry_after


_AUTHENTICATION_CODES = frozenset(
    ["unauthorized", "tier_insufficient", "forbidden", "key_revoked"]
)
_VALIDATION_CODES = frozenset(
    ["invalid_vat_format", "missing_parameter", "validation_error", "invalid_json"]
)
_RATE_LIMIT_CODES = frozenset(["rate_limit_exceeded", "burst_limit_exceeded"])
_UPSTREAM_CODES = frozenset(["upstream_unavailable", "upstream_member_state_unavailable"])


def _raise_for_error(
    status_code: int,
    body: Any,
    headers: Any,
) -> None:
    error_obj: Dict[str, Any] = {}
    meta: Dict[str, Any] = {}

    if isinstance(body, dict):
        error_obj = body.get("error", body)
        if not isinstance(error_obj, dict):
            error_obj = {}
        meta = body.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}

    message: str = error_obj.get("message", f"HTTP {status_code}")
    code: str = error_obj.get("code", "unknown_error")
    docs_url: str = error_obj.get("docs_url", "")
    details_raw = error_obj.get("details")
    details: Optional[List[Dict[str, str]]] = (
        details_raw if isinstance(details_raw, list) else None
    )

    request_id: Optional[str] = meta.get("request_id")
    if request_id is None and hasattr(headers, "get"):
        request_id = headers.get("x-request-id")

    retry_after_raw = headers.get("retry-after") if hasattr(headers, "get") else None
    retry_after: Optional[float] = None
    if retry_after_raw is not None:
        try:
            retry_after = float(retry_after_raw)
        except (ValueError, TypeError):
            pass

    if code in _AUTHENTICATION_CODES:
        raise AuthenticationError(message, code, status_code, request_id, docs_url)
    if code in _VALIDATION_CODES:
        raise ValidationError(message, code, status_code, request_id, docs_url, details)
    if code in _RATE_LIMIT_CODES:
        raise RateLimitError(message, code, status_code, request_id, docs_url, retry_after)
    if code in _UPSTREAM_CODES:
        raise UpstreamError(message, code, status_code, request_id, docs_url, retry_after)

    raise AvatcadoError(message, code, status_code, request_id, docs_url, details)
