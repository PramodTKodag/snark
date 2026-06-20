import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            from google import genai
        except ImportError:
            raise ProviderError(
                "google-genai package not installed. Run: poetry add google-genai"
            )

        env_var = getattr(settings, "GEMINI_API_KEY_ENV_VAR", "GEMINI_API_KEY")
        self._api_key = api_key or os.environ.get(env_var, "")
        self._model_name = model or getattr(
            settings, "AI_DEFAULT_MODEL", "gemini-2.0-flash"
        )

        if self._api_key:
            logger.info(
                "GeminiProvider init: api_key=%s, model=%s",
                "set",
                self._model_name,
            )
            self._client = genai.Client(api_key=self._api_key)
        else:
            logger.warning(
                "GeminiProvider init: NO API key found! env_var=%s",
                env_var,
            )
            self._client = genai.Client(api_key="missing")

    @property
    def name(self) -> str:
        return "gemini"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
        from google.genai import types

        start = time.monotonic()
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
        except Exception as exc:
            logger.error("Gemini API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Gemini API call failed: {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.text if response.text else ""
        tokens_used = 0
        if response.usage_metadata:
            tokens_used = (
                (response.usage_metadata.prompt_token_count or 0)
                + (response.usage_metadata.candidates_token_count or 0)
            )

        return AIResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model_name,
            provider=self.name,
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        try:
            self._client.models.generate_content(
                model=self._model_name,
                contents="ping",
            )
            return True
        except Exception:
            return False
