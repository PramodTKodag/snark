from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

MAX_ERROR_SUMMARY_LENGTH = 300


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


def _scrub(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def safe_error_summary(exc: BaseException, secrets: Iterable[str]) -> str:
    """Describe a provider failure without leaking credentials.

    Auth failures (HTTP 401/403) reduce to the exception class and status, since
    their bodies can echo the credential. Anything else keeps the message, and
    the direct cause's class and message when there is one (the SDK wraps DNS,
    refused-connection and TLS errors), with every secret value replaced by
    ``***``, truncated to fit ``error_detail``.
    """
    summary = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        summary += f" (status {status})"
        if status in (401, 403):
            return summary
    message = _scrub(str(exc), secrets)
    if message:
        summary += f": {message}"
    cause = exc.__cause__
    if cause is not None:
        cause_message = _scrub(str(cause), secrets)
        summary += f" (caused by {type(cause).__name__}"
        summary += f": {cause_message})" if cause_message else ")"
    return summary[:MAX_ERROR_SUMMARY_LENGTH]


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

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
