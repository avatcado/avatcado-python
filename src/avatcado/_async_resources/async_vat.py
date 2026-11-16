from __future__ import annotations

from typing import List, Optional

import httpx

from avatcado import _operations as ops
from avatcado._base_client import arequest
from avatcado._config import AvatcadoConfig
from avatcado._types import AsyncBatchValidateResponse, AsyncValidateResponse


class AsyncVatAsyncResource:
    """Queued validation: the API accepts the request and delivers the result by webhook.

    "Async" here names the API's queued endpoints, not Python's ``async``. This resource is
    blocking on :class:`avatcado.Avatcado` and awaitable on :class:`avatcado.AsyncAvatcado`.
    """

    def __init__(self, http: httpx.AsyncClient, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    async def validate(
        self,
        vat_number: str,
        *,
        requester_vat_number: Optional[str] = None,
        cache: Optional[bool] = None,
        fallback: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> AsyncValidateResponse:
        """Queue one VAT number. ``cache`` and ``fallback`` behave as on ``vat.validate()``."""
        call = ops.async_validate_call(
            vat_number, requester_vat_number, cache, fallback, request_id
        )
        return ops.parse_async_validate(await arequest(self._http, self._config, call))

    async def validate_batch(
        self,
        vat_numbers: List[str],
        *,
        requester_vat_number: Optional[str] = None,
        cache: Optional[bool] = None,
        fallback: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> AsyncBatchValidateResponse:
        """Queue up to 200 (Pro) or 1,000 (Business) VAT numbers.

        Rejected items come back flat: ``item.vat_number``, ``item.error_code`` and
        ``item.error_message``.
        """
        call = ops.async_validate_batch_call(
            vat_numbers, requester_vat_number, cache, fallback, request_id
        )
        return ops.parse_async_validate_batch(await arequest(self._http, self._config, call))
