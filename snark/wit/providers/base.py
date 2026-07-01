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
    input_tokens: int = field(default=0)
    output_tokens: int = field(default=0)


@dataclass
class StreamUsage:
    """Terminal marker yielded by ``generate_stream`` carrying token usage.

    Streaming yields text deltas (``str``) as they arrive, then finally one of
    these so the caller can log accurate token counts. Consumers must skip it
    when forwarding deltas to the client (it is not response text).
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def tokens_used(self) -> int:
        return self.input_tokens + self.output_tokens


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
    ) -> Iterator[str | StreamUsage]:
        """Yield response text deltas, then a final ``StreamUsage``.

        Default implementation falls back to the non-streaming ``generate`` and
        yields the whole response as a single chunk, so providers that do not
        implement token streaming still work over the streaming transport.
        Providers that support it override this to yield token-by-token. Either
        way the last item is a ``StreamUsage`` so callers can log token counts.
        """
        result = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result.text:
            yield result.text
        yield StreamUsage(
            input_tokens=result.input_tokens, output_tokens=result.output_tokens
        )

    def is_available(self) -> bool:
        """Whether this provider is configured and usable. Overridden per provider."""
        return True
