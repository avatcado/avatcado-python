from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Optional

from avatcado._errors import AvatcadoError

_DEFAULT_BASE_URL = "https://api.avatcado.com"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 0
_DEFAULT_MAX_RETRY_DELAY = 60.0
# "vtly_" keys were minted before the rebrand; the API accepts them permanently.
_KEY_PREFIXES = ("avat_live_", "avat_test_", "vtly_live_", "vtly_test_")


@dataclass
class AvatcadoConfig:
    api_key: str
    base_url: str
    timeout: float
    max_retries: int = _DEFAULT_MAX_RETRIES
    max_retry_delay: float = _DEFAULT_MAX_RETRY_DELAY

    @classmethod
    def resolve(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_retry_delay: Optional[float] = None,
    ) -> AvatcadoConfig:
        resolved_key = api_key or os.environ.get("AVATCADO_API_KEY", "")

        if not resolved_key:
            raise AvatcadoError(
                "No API key provided. Pass it to the constructor or set the "
                "AVATCADO_API_KEY environment variable.",
                code="missing_api_key",
                status_code=0,
            )

        if not resolved_key.startswith(_KEY_PREFIXES):
            warnings.warn(
                "The API key does not start with 'avat_live_' or 'avat_test_'. "
                "This may indicate an invalid key.",
                stacklevel=3,
            )

        return cls(
            api_key=resolved_key,
            base_url=base_url or _DEFAULT_BASE_URL,
            timeout=timeout if timeout is not None else _DEFAULT_TIMEOUT,
            max_retries=(
                max(0, int(max_retries)) if max_retries is not None else _DEFAULT_MAX_RETRIES
            ),
            max_retry_delay=(
                max(0.0, float(max_retry_delay))
                if max_retry_delay is not None
                else _DEFAULT_MAX_RETRY_DELAY
            ),
        )
