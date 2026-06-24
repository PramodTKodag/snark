import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)

# Gemini candidate finish reasons that indicate a safety/content block.
_GEMINI_SAFETY_FINISH = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "IMAGE_SAFETY",
}


class GeminiProvider(AIProvider):
    """Google Gemini provider (new google-genai SDK)."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            from google import genai
        except ImportError:
            self._unavailable_reason = "google-genai package not installed"
            logger.warning("GeminiProvider unavailable: %s", self._unavailable_reason)
            return

        env_var = getattr(settings, "GEMINI_API_KEY_ENV_VAR", "GEMINI_API_KEY")
        self._api_key = api_key if api_key is not None else os.environ.get(env_var, "")
        self._model_name = model or getattr(
            settings, "GEMINI_MODEL", "gemini-2.0-flash"
        )

        if not self._api_key:
            self._unavailable_reason = f"no API key (set {env_var})"
            logger.warning("GeminiProvider unavailable: %s", self._unavailable_reason)
            return

        self._client = genai.Client(api_key=self._api_key)
        logger.info("GeminiProvider ready: model=%s", self._model_name)

    @property
    def name(self) -> str:
        return "gemini"

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
                f"Gemini provider unavailable: {self._unavailable_reason}"
            )

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

        self._raise_if_blocked(response)

        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            text = response.text or ""
        except ValueError:
            # `.text` raises when no usable candidate was returned (blocked output).
            raise ContentFilterError("Gemini returned no usable content (blocked)")

        tokens_used = 0
        if response.usage_metadata:
            tokens_used = (response.usage_metadata.prompt_token_count or 0) + (
                response.usage_metadata.candidates_token_count or 0
            )

        return AIResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model_name,
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
                f"Gemini provider unavailable: {self._unavailable_reason}"
            )

        from google.genai import types

        try:
            stream = self._client.models.generate_content_stream(
                model=self._model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            for chunk in stream:
                self._raise_if_blocked(chunk)
                try:
                    text = chunk.text or ""
                except (ValueError, AttributeError):
                    text = ""
                if text:
                    yield text
        except ContentFilterError:
            raise
        except Exception as exc:
            logger.error("Gemini streaming error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Gemini streaming failed: {exc}") from exc

    @staticmethod
    def _raise_if_blocked(response) -> None:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None and getattr(
            prompt_feedback, "block_reason", None
        ):
            reason = getattr(
                prompt_feedback.block_reason, "name", str(prompt_feedback.block_reason)
            )
            logger.warning("Gemini blocked prompt: %s", reason)
            raise ContentFilterError(f"Gemini blocked the prompt: {reason}")

        for candidate in getattr(response, "candidates", None) or []:
            finish = getattr(candidate, "finish_reason", None)
            name = getattr(finish, "name", str(finish)) if finish is not None else None
            if name in _GEMINI_SAFETY_FINISH:
                logger.warning("Gemini safety finish_reason: %s", name)
                raise ContentFilterError(f"Gemini safety block: {name}")

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.models.generate_content(
                model=self._model_name,
                contents="ping",
            )
            return True
        except Exception:
            return False
