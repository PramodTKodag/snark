import logging
import os
import time

import anthropic
from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        env_var = getattr(settings, "ANTHROPIC_API_KEY_ENV_VAR", "ANTHROPIC_API_KEY")
        self._api_key = api_key or os.environ.get(env_var, "")
        self._model = model or getattr(
            settings, "AI_DEFAULT_MODEL", "claude-haiku-4-20250414"
        )
        if self._api_key:
            logger.info(
                "ClaudeProvider init: api_key=%s, model=%s",
                "set",
                self._model,
            )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        else:
            logger.warning(
                "ClaudeProvider init: NO API key found! env_var=%s",
                env_var,
            )
            self._client = anthropic.Anthropic(api_key="missing")

    @property
    def name(self) -> str:
        return "claude"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
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
                raise ContentFilterError(f"Claude content filter blocked response: {exc}") from exc
            logger.error("Claude bad request [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except anthropic.APIError as exc:
            logger.error("Claude API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except Exception as exc:
            logger.error("Claude provider unexpected error [%s]: %s", type(exc).__name__, exc)
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
        try:
            self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
