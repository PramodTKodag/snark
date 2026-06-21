import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            import anthropic
        except ImportError:
            self._unavailable_reason = "anthropic package not installed"
            logger.warning("ClaudeProvider unavailable: %s", self._unavailable_reason)
            return

        self._anthropic = anthropic
        env_var = getattr(settings, "ANTHROPIC_API_KEY_ENV_VAR", "ANTHROPIC_API_KEY")
        self._api_key = api_key if api_key is not None else os.environ.get(env_var, "")
        self._model = model or getattr(
            settings, "CLAUDE_MODEL", "claude-haiku-4-5-20251001"
        )

        if not self._api_key:
            self._unavailable_reason = f"no API key (set {env_var})"
            logger.warning("ClaudeProvider unavailable: %s", self._unavailable_reason)
            return

        self._client = anthropic.Anthropic(api_key=self._api_key)
        logger.info("ClaudeProvider ready: model=%s", self._model)

    @property
    def name(self) -> str:
        return "claude"

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
                f"Claude provider unavailable: {self._unavailable_reason}"
            )

        anthropic = self._anthropic
        start = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.BadRequestError as exc:
            if "content filtering" in str(exc).lower() or "blocked" in str(exc).lower():
                logger.warning("Claude content filter triggered: %s", exc)
                raise ContentFilterError(
                    f"Claude content filter blocked response: {exc}"
                ) from exc
            logger.error("Claude bad request [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except anthropic.APIError as exc:
            logger.error("Claude API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except Exception as exc:
            logger.error(
                "Claude provider unexpected error [%s]: %s", type(exc).__name__, exc
            )
            raise ProviderError(f"Claude provider error: {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.content[0].text if response.content else ""
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return AIResponse(
            text=text,
            tokens_used=tokens,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
