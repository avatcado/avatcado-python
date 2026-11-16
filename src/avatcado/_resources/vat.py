from __future__ import annotations

from typing import List, Optional

import httpx

from avatcado import _operations as ops
from avatcado._base_client import request
from avatcado._config import AvatcadoConfig
from avatcado._types import BatchValidateResponse, ValidateResponse


class VatResource:
    def __init__(self, http: httpx.Client, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    def validate(
        self,
        vat_number: str,
        *,
        requester_vat_number: Optional[str] = None,
        cache: Optional[bool] = None,
        fallback: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> ValidateResponse:
        """Validate one VAT number.

        ``cache`` and ``fallback`` are sent only when you set them. Unset, the API default
        applies: both on, and both off when ``requester_vat_number`` is given. ``cache=False``
        forces a fresh lookup; ``cache=True`` next to a requester accepts a cached or stored
        result. ``fallback=False`` stops a VIES outage from being answered by a national
        register; ``fallback=True`` next to a requester accepts a register answer, which
        carries no consultation number. ``fallback`` applies on Pro and Business plans.
        """
        call = ops.validate_call(vat_number, requester_vat_number, cache, fallback, request_id)
        return ops.parse_validate(request(self._http, self._config, call))

    def validate_batch(
        self,
        vat_numbers: List[str],
        *,
        requester_vat_number: Optional[str] = None,
        cache: Optional[bool] = None,
        fallback: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> BatchValidateResponse:
        """Validate up to 50 VAT numbers in one request. Pro and Business plans.

        ``cache`` and ``fallback`` behave as on :meth:`validate` and apply to every item.
        """
        call = ops.validate_batch_call(
            vat_numbers, requester_vat_number, cache, fallback, request_id
        )
        return ops.parse_validate_batch(request(self._http, self._config, call))
