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

# Gemini candidate finish reasons that indicate a safety/content block.
_GEMINI_SAFETY_FINISH = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "IMAGE_SAFETY",
}


class GeminiProvider(AIProvider):
    """Google Gemini provider (google-genai SDK), built from a ``ProviderSpec``.

    The caller resolves the API key; this class never reads the environment.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        self._spec = spec
        self._api_key = api_key
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            from google import genai
        except ImportError:
            self._unavailable_reason = "google-genai package not installed"
            logger.warning(
                "Provider %s unavailable: %s", spec.name, self._unavailable_reason
            )
            return

        if not api_key:
            self._unavailable_reason = f"no API key (set {spec.key_env})"
            return

        self._client = genai.Client(api_key=api_key)
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

    def is_available(self) -> bool:
        return self._client is not None

    def _safety_settings(self):
        """Gemini 2.5/3 default safety thresholds are effectively OFF, so set
        them explicitly. BLOCK_ONLY_HIGH lets mild roast edginess through while
        still blocking genuinely harmful content."""
        from google.genai import types

        return [
            types.SafetySetting(
                category=category,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            )
            for category in (
                types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            )
        ]

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

        from google.genai import types

        start = time.monotonic()
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    safety_settings=self._safety_settings(),
                ),
            )
        except Exception as exc:
            raise self._failure("API call failed", exc) from None

        self._raise_if_blocked(response)

        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            text = response.text or ""
        except ValueError:
            # `.text` raises when no usable candidate was returned (blocked output).
            raise ContentFilterError("Gemini returned no usable content (blocked)")

        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

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

        from google.genai import types

        try:
            stream = self._client.models.generate_content_stream(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    safety_settings=self._safety_settings(),
                ),
            )
            input_tokens = 0
            output_tokens = 0
            for chunk in stream:
                self._raise_if_blocked(chunk)
                meta = getattr(chunk, "usage_metadata", None)
                if meta:
                    input_tokens = meta.prompt_token_count or 0
                    output_tokens = meta.candidates_token_count or 0
                try:
                    text = chunk.text or ""
                except (ValueError, AttributeError):
                    text = ""
                if text:
                    yield text
            yield StreamUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        except ContentFilterError:
            raise
        except Exception as exc:
            raise self._failure("streaming failed", exc) from None

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
                model=self.model,
                contents="ping",
            )
            return True
        except Exception:
            return False
