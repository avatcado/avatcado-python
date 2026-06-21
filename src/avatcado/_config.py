from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import Optional

from avatcado._errors import AvatcadoError

_DEFAULT_BASE_URL = "https://api.avatcado.com"
_DEFAULT_TIMEOUT = 30.0


@dataclass
class AvatcadoConfig:
    api_key: str
    base_url: str
    timeout: float

    @classmethod
    def resolve(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AvatcadoConfig:
        resolved_key = api_key or os.environ.get("AVATCADO_API_KEY", "")

        if not resolved_key:
            raise AvatcadoError(
                "No API key provided. Pass it to the constructor or set the "
                "AVATCADO_API_KEY environment variable.",
                code="missing_api_key",
                status_code=0,
            )

        if not resolved_key.startswith(("avat_live_", "avat_test_")):
            warnings.warn(
                "The API key does not start with 'avat_live_' or 'avat_test_'. "
                "This may indicate an invalid key.",
                stacklevel=3,
            )

        return cls(
            api_key=resolved_key,
            base_url=base_url or _DEFAULT_BASE_URL,
            timeout=timeout if timeout is not None else _DEFAULT_TIMEOUT,
        )
