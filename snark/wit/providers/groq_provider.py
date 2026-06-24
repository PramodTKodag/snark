import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq chat-completions provider (OpenAI-compatible API)."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            from groq import Groq
        except ImportError:
            self._unavailable_reason = "groq package not installed"
            logger.warning("GroqProvider unavailable: %s", self._unavailable_reason)
            return

        env_var = getattr(settings, "GROQ_API_KEY_ENV_VAR", "GROQ_API_KEY")
        self._api_key = api_key if api_key is not None else os.environ.get(env_var, "")
        self._model = model or getattr(
            settings, "GROQ_MODEL", "llama-3.3-70b-versatile"
        )

        if not self._api_key:
            self._unavailable_reason = f"no API key (set {env_var})"
            logger.warning("GroqProvider unavailable: %s", self._unavailable_reason)
            return

        self._client = Groq(api_key=self._api_key)
        logger.info("GroqProvider ready: model=%s", self._model)

    @property
    def name(self) -> str:
        return "groq"

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
                f"Groq provider unavailable: {self._unavailable_reason}"
            )

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

        choice = response.choices[0] if response.choices else None
        if (
            choice is not None
            and getattr(choice, "finish_reason", None) == "content_filter"
        ):
            logger.warning(
                "Groq content filter triggered (finish_reason=content_filter)"
            )
            raise ContentFilterError("Groq content filter blocked the response")

        latency_ms = int((time.monotonic() - start) * 1000)
        text = choice.message.content if choice else ""
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

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ):
        if self._client is None:
            raise ProviderError(
                f"Groq provider unavailable: {self._unavailable_reason}"
            )

        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if getattr(choice, "finish_reason", None) == "content_filter":
                    raise ContentFilterError("Groq content filter blocked the response")
                delta = choice.delta.content or ""
                if delta:
                    yield delta
        except ContentFilterError:
            raise
        except Exception as exc:
            logger.error("Groq streaming error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Groq streaming failed: {exc}") from exc

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.chat.completions.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
