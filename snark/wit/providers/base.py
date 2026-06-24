from abc import ABC, abstractmethod
from collections.abc import Iterator
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

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> Iterator[str]:
        """Yield response text deltas as they are produced.

        Default implementation falls back to the non-streaming ``generate`` and
        yields the whole response as a single chunk, so providers that do not
        implement token streaming still work over the streaming transport.
        Providers that support it override this to yield token-by-token.
        """
        result = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result.text:
            yield result.text

    def is_available(self) -> bool:
        """Whether this provider is configured and usable. Overridden per provider."""
        return True
