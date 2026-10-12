import copy
import logging
import time
from collections.abc import Iterator

import openai

from .base import (
    AIResponse,
    ContentFilterError,
    ProviderError,
    StreamUsage,
    safe_error_summary,
)
from .config import ProviderSpec
from .spec_backed import SpecBackedProvider, ambient_header_names

logger = logging.getLogger(__name__)

# Sent as the bearer token to keyless backends (e.g. a local Ollama). The SDK
# refuses an empty key and would otherwise fall back to OPENAI_API_KEY.
KEYLESS_PLACEHOLDER_API_KEY = "keyless"
REQUEST_TIMEOUT = openai.Timeout(60.0, connect=5.0)
MAX_RETRIES = 2
CUSTOM_HEADERS_ENV = "OPENAI_CUSTOM_HEADERS"


class OpenAICompatibleProvider(SpecBackedProvider):
    """Chat-completions provider for any OpenAI-compatible endpoint.

    Serves Groq, Ollama, OpenRouter, vLLM and the like from a ``ProviderSpec``.
    The configured key and url are the only credentials and endpoint used;
    ambient ``OPENAI_*`` settings are suppressed.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        super().__init__(spec, api_key)

        if spec.key_env and not api_key:
            self._unavailable_reason = f"no API key (set {spec.key_env})"
            return

        bearer_key = api_key or KEYLESS_PLACEHOLDER_API_KEY
        self._client = openai.OpenAI(
            api_key=bearer_key,
            base_url=spec.url,
            timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
            default_headers={
                # The SDK adds these from OPENAI_ORG_ID / OPENAI_PROJECT_ID and
                # OPENAI_CUSTOM_HEADERS unless told to omit them; Omit() keeps
                # the environment off the wire.
                **{
                    name: openai.Omit()
                    for name in ambient_header_names(CUSTOM_HEADERS_ENV)
                },
                "OpenAI-Organization": openai.Omit(),
                "OpenAI-Project": openai.Omit(),
                # An explicit header makes the SDK discard any Authorization
                # injected through OPENAI_CUSTOM_HEADERS.
                "Authorization": f"Bearer {bearer_key}",
            },
            # Requests carry prompts and a bearer token: never follow redirects
            # and never route through proxies or CA bundles from the environment.
            http_client=openai.DefaultHttpxClient(
                follow_redirects=False, trust_env=False
            ),
        )
        logger.info("Provider %s ready: model=%s", spec.name, spec.model)

    def _request_kwargs(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> dict:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "extra_body": copy.deepcopy(self._spec.extra_body or {}),
        }

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
        client = self._require_client()
        kwargs = self._request_kwargs(
            system_prompt, user_prompt, temperature, max_tokens
        )

        start = time.monotonic()
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise self._failure("API call failed", exc) from None

        choice = response.choices[0] if response.choices else None
        if choice is None:
            raise ProviderError(f"{self.name} returned no choices")
        if getattr(choice, "finish_reason", None) == "content_filter":
            logger.warning(
                "%s content filter triggered (finish_reason=content_filter)",
                self.name,
            )
            raise ContentFilterError(f"{self.name} content filter blocked the response")

        message = getattr(choice, "message", None)
        if message is None:
            raise ProviderError(f"{self.name} returned no message")
        text = message.content
        if not text:
            raise ProviderError(f"{self.name} returned an empty response")

        latency_ms = int((time.monotonic() - start) * 1000)
        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0

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
    ) -> Iterator[str | StreamUsage]:
        client = self._require_client()
        kwargs = self._request_kwargs(
            system_prompt, user_prompt, temperature, max_tokens
        )

        try:
            with client.chat.completions.create(
                **kwargs, stream=True, stream_options={"include_usage": True}
            ) as stream:
                input_tokens = 0
                output_tokens = 0
                produced_text = False
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
                        raise ContentFilterError(
                            f"{self.name} content filter blocked the response"
                        )
                    delta = choice.delta.content or ""
                    if delta:
                        produced_text = True
                        yield delta
                if not produced_text:
                    raise ProviderError(f"{self.name} returned an empty stream")
                yield StreamUsage(
                    input_tokens=input_tokens, output_tokens=output_tokens
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise self._failure("streaming failed", exc) from None

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.chat.completions.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:
            logger.warning(
                "%s health check failed: %s",
                self.name,
                safe_error_summary(exc, [self._api_key]),
            )
            return False
