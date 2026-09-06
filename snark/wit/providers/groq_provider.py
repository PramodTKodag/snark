import logging
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError, StreamUsage

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq chat-completions provider (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            from groq import Groq
        except ImportError:
            self._unavailable_reason = "groq package not installed"
            logger.warning("GroqProvider unavailable: %s", self._unavailable_reason)
            return

        self._api_key = (
            api_key if api_key is not None else getattr(settings, "GROQ_API_KEY", "")
        )
        self._model = model or getattr(settings, "GROQ_MODEL", "openai/gpt-oss-20b")
        self._reasoning_effort = (
            reasoning_effort
            if reasoning_effort is not None
            else getattr(settings, "GROQ_REASONING_EFFORT", "")
        )

        if not self._api_key:
            self._unavailable_reason = "no API key (set GROQ_API_KEY)"
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

        request_kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self._reasoning_effort:
            request_kwargs["reasoning_effort"] = self._reasoning_effort

        start = time.monotonic()
        try:
            response = self._client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            # Non-reasoning models reject reasoning_effort; drop it and retry once
            # so the same config works across the whole model lineup.
            if "reasoning_effort" in request_kwargs and "reasoning_effort" in str(exc):
                logger.warning(
                    "Model %s does not support reasoning_effort; retrying without it",
                    self._model,
                )
                request_kwargs.pop("reasoning_effort")
                try:
                    response = self._client.chat.completions.create(**request_kwargs)
                except Exception as retry_exc:
                    logger.error(
                        "Groq API error [%s]: %s",
                        type(retry_exc).__name__,
                        retry_exc,
                    )
                    raise ProviderError(
                        f"Groq API call failed: {retry_exc}"
                    ) from retry_exc
            else:
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
        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0

        return AIResponse(
            text=text,
            tokens_used=input_tokens + output_tokens,
            model=self._model,
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
                # The groq SDK (0.13.x) has no `stream_options` kwarg — passing
                # it raises TypeError and breaks every stream. Forward it via
                # `extra_body` so the API still emits a final usage chunk.
                extra_body={"stream_options": {"include_usage": True}},
            )
            input_tokens = 0
            output_tokens = 0
            for chunk in stream:
                # include_usage emits a final choice-less chunk carrying usage.
                usage = getattr(chunk, "usage", None)
                if usage:
                    input_tokens = usage.prompt_tokens or 0
                    output_tokens = usage.completion_tokens or 0
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if getattr(choice, "finish_reason", None) == "content_filter":
                    raise ContentFilterError("Groq content filter blocked the response")
                delta = choice.delta.content or ""
                if delta:
                    yield delta
            yield StreamUsage(input_tokens=input_tokens, output_tokens=output_tokens)
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
