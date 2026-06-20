import logging

from .base import AIProvider, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class _ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, type[AIProvider]] = {}
        self._instances: dict[str, AIProvider] = {}
        self._default: str | None = None
        self._fallback_order: list[str] = []

    def register(self, name: str, provider_class: type[AIProvider], default: bool = False):
        self._providers[name] = provider_class
        if default or self._default is None:
            self._default = name
        if name not in self._fallback_order:
            self._fallback_order.append(name)
        logger.debug("Registered AI provider: %s (default=%s)", name, default)

    def get(self, name: str | None = None) -> AIProvider:
        target = name or self._default
        if target is None:
            raise ValueError("No AI providers registered")
        if target not in self._providers:
            raise ValueError(f"Unknown AI provider: {target}")
        if target not in self._instances:
            self._instances[target] = self._providers[target]()
        return self._instances[target]

    def get_fallbacks(self, exclude: str | None = None) -> list[AIProvider]:
        """Return providers in fallback order, excluding the named one."""
        result = []
        for name in self._fallback_order:
            if name == exclude:
                continue
            try:
                result.append(self.get(name))
            except Exception:
                continue
        return result

    def reset(self):
        self._instances.clear()


ProviderRegistry = _ProviderRegistry()

# Auto-register providers — Groq is default (free tier), others as fallback
from .claude_provider import ClaudeProvider  # noqa: E402
from .gemini_provider import GeminiProvider  # noqa: E402
from .groq_provider import GroqProvider  # noqa: E402

ProviderRegistry.register("groq", GroqProvider, default=True)
ProviderRegistry.register("gemini", GeminiProvider)
ProviderRegistry.register("claude", ClaudeProvider)
