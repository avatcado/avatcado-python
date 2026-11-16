from __future__ import annotations

from typing import Optional

import httpx

from avatcado import _operations as ops
from avatcado._base_client import request
from avatcado._config import AvatcadoConfig
from avatcado._types import EoriValidateResponse


class EoriResource:
    def __init__(self, http: httpx.Client, config: AvatcadoConfig) -> None:
        self._http = http
        self._config = config

    def validate(
        self,
        eori_number: str,
        *,
        cache: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> EoriValidateResponse:
        """Check one EORI number against the register that issued it.

        GB numbers are checked with HMRC; numbers from the 27 EU member states and XI with
        the European Commission's EORI validation service. Pass ``cache=False`` to skip the
        cache and ask the register again. Unset means the API default (the cache is used).
        """
        call = ops.eori_validate_call(eori_number, cache, request_id)
        return ops.parse_eori_validate(request(self._http, self._config, call))
