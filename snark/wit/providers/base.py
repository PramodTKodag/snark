from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AIResponse:
    text: str
    tokens_used: int
    model: str
    provider: str
    latency_ms: int = field(default=0)


class ProviderError(Exception):
    """Raised when an AI provider fails to generate a response."""


class ContentFilterError(ProviderError):
    """Raised when a provider blocks output due to content filtering."""


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    def is_available(self) -> bool:
        """Whether this provider is configured and usable. Overridden per provider."""
        return True
