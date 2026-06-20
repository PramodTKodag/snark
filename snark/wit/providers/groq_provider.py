import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ProviderError

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            from groq import Groq
        except ImportError:
            raise ProviderError(
                "groq package not installed. Run: poetry add groq"
            )

        env_var = getattr(settings, "GROQ_API_KEY_ENV_VAR", "GROQ_API_KEY")
        self._api_key = api_key or os.environ.get(env_var, "")
        self._model = model or getattr(
            settings, "AI_DEFAULT_MODEL", "llama-3.3-70b-versatile"
        )

        if self._api_key:
            logger.info(
                "GroqProvider init: api_key=%s, model=%s",
                "set",
                self._model,
            )
            self._client = Groq(api_key=self._api_key)
        else:
            logger.warning(
                "GroqProvider init: NO API key found! env_var=%s",
                env_var,
            )
            self._client = Groq(api_key="missing")

    @property
    def name(self) -> str:
        return "groq"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
        start = time.monotonic()
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            logger.error("Groq API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Groq API call failed: {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content if response.choices else ""
        tokens_used = 0
        if response.usage:
            tokens_used = (response.usage.prompt_tokens or 0) + (
                response.usage.completion_tokens or 0
            )

        return AIResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        try:
            self._client.chat.completions.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
