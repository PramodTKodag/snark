import logging
import time

import httpx

from .base import AIResponse, ContentFilterError, StreamUsage
from .config import ProviderSpec
from .spec_backed import SpecBackedProvider, ambient_header_names

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.anthropic.com"
CUSTOM_HEADERS_ENV = "ANTHROPIC_CUSTOM_HEADERS"


class ClaudeProvider(SpecBackedProvider):
    """Anthropic Claude provider, built from a ``ProviderSpec``.

    The caller resolves the API key. The key and ``API_BASE_URL`` are the only
    credential and endpoint used; ambient ``ANTHROPIC_*`` settings, proxies and
    CA bundles are suppressed.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        super().__init__(spec, api_key)

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

        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=API_BASE_URL,
            default_headers={
                # The SDK adds these from ANTHROPIC_CUSTOM_HEADERS unless told
                # to omit them; Omit() keeps the environment off the wire.
                **{
                    name: anthropic.Omit()
                    for name in ambient_header_names(CUSTOM_HEADERS_ENV)
                },
                "Authorization": anthropic.Omit(),
            },
            # Requests carry prompts and the API key: never follow redirects
            # and never route through proxies or CA bundles from the environment.
            # An explicit transport stops the SDK from reading proxies out of
            # the environment (it ignores trust_env for that).
            http_client=anthropic.DefaultHttpxClient(
                transport=httpx.HTTPTransport(
                    trust_env=False, limits=anthropic.DEFAULT_CONNECTION_LIMITS
                ),
                follow_redirects=False,
                trust_env=False,
            ),
        )
        logger.info("Provider %s ready: model=%s", spec.name, spec.model)

    def _is_content_filter(self, exc: Exception) -> bool:
        return "content filtering" in str(exc).lower()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 200,
    ) -> AIResponse:
        client = self._require_client()
        anthropic = self._anthropic
        start = time.monotonic()
        try:
            response = client.messages.create(
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
        client = self._require_client()
        anthropic = self._anthropic
        try:
            with client.messages.stream(
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
