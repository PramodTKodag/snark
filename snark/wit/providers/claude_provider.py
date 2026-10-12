import logging
import time

from .base import (
    AIProvider,
    AIResponse,
    ContentFilterError,
    ProviderError,
    StreamUsage,
    safe_error_summary,
)
from .config import ProviderSpec

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider, built from a ``ProviderSpec``.

    The caller resolves the API key; this class never reads the environment.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        self._spec = spec
        self._api_key = api_key
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            import anthropic
        except ImportError:
            self._unavailable_reason = "anthropic package not installed"
            logger.warning(
                "Provider %s unavailable: %s", spec.name, self._unavailable_reason
            )
            return

        self._anthropic = anthropic

        if not api_key:
            self._unavailable_reason = f"no API key (set {spec.key_env})"
            return

        self._client = anthropic.Anthropic(api_key=api_key)
        logger.info("Provider %s ready: model=%s", spec.name, spec.model)

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def model(self) -> str:
        return self._spec.model

    def _failure(self, action: str, exc: Exception) -> ProviderError:
        summary = safe_error_summary(exc, [self._api_key])
        logger.error("%s %s: %s", self.name, action, summary)
        return ProviderError(f"{self.name} {action}: {summary}")

    def _is_content_filter(self, exc: Exception) -> bool:
        return "content filtering" in str(exc).lower()

    def is_available(self) -> bool:
        return self._client is not None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
        if self._client is None:
            raise ProviderError(
                f"{self.name} provider unavailable: {self._unavailable_reason}"
            )

        anthropic = self._anthropic
        start = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.BadRequestError as exc:
            if self._is_content_filter(exc):
                logger.warning("%s content filter triggered", self.name)
                raise ContentFilterError(
                    f"{self.name} content filter blocked the response"
                ) from None
            raise self._failure("API call failed", exc) from None
        except Exception as exc:
            raise self._failure("API call failed", exc) from None

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.content[0].text if response.content else ""
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return AIResponse(
            text=text,
            tokens_used=input_tokens + output_tokens,
            model=self.model,
            provider=self.name,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ):
        if self._client is None:
            raise ProviderError(
                f"{self.name} provider unavailable: {self._unavailable_reason}"
            )

        anthropic = self._anthropic
        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
                usage = stream.get_final_message().usage
                yield StreamUsage(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                )
        except anthropic.BadRequestError as exc:
            if self._is_content_filter(exc):
                logger.warning("%s content filter triggered", self.name)
                raise ContentFilterError(
                    f"{self.name} content filter blocked the response"
                ) from None
            raise self._failure("streaming failed", exc) from None
        except Exception as exc:
            raise self._failure("streaming failed", exc) from None

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
