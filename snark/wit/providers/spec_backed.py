import logging
import os
from typing import Any

from .base import AIProvider, ProviderError, safe_error_summary
from .config import ProviderSpec

logger = logging.getLogger(__name__)


def ambient_header_names(env_var: str) -> list[str]:
    """Header names an SDK would add from a ``Name: value``-per-line env var.

    Parsed the way the SDKs do so each can be omitted explicitly;
    ``Authorization`` is skipped because it is pinned separately.
    """
    names = []
    for line in os.environ.get(env_var, "").split("\n"):
        name = line[: line.find(":")].strip() if ":" in line else ""
        if name and name.lower() != "authorization":
            names.append(name)
    return names


class SpecBackedProvider(AIProvider):
    """Provider configured by a ``ProviderSpec`` and a caller-resolved API key.

    Holds what every adapter shares, including ``_failure``, the one path that
    scrubs the API key out of upstream errors. Adapters build ``_client`` (or
    set ``_unavailable_reason``) and keep only the SDK-specific calls.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        self._spec = spec
        self._api_key = api_key
        self._client: Any = None
        self._unavailable_reason: str | None = None

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def model(self) -> str:
        return self._spec.model

    def is_available(self) -> bool:
        return self._client is not None

    def _require_client(self) -> Any:
        if self._client is None:
            raise ProviderError(
                f"{self.name} provider unavailable: {self._unavailable_reason}"
            )
        return self._client

    def _failure(self, action: str, exc: Exception) -> ProviderError:
        summary = safe_error_summary(exc, [self._api_key])
        logger.error("%s %s: %s", self.name, action, summary)
        return ProviderError(f"{self.name} {action}: {summary}")
