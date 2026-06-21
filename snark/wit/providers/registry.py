import logging

from django.conf import settings

from .base import AIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider

logger = logging.getLogger(__name__)

# All known provider implementations, keyed by their canonical name.
PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
}


class _ProviderRegistry:
    """Resolves provider instances from Django settings.

    The default provider and fallback order live in settings (single source of
    truth). Instances are created lazily and cached for the process lifetime.
    """

    def __init__(self):
        self._instances: dict[str, AIProvider] = {}

    def _default_name(self) -> str:
        return getattr(settings, "AI_DEFAULT_PROVIDER", "groq")

    def _fallback_order(self) -> list[str]:
        return list(
            getattr(
                settings, "AI_PROVIDER_FALLBACK_ORDER", ["groq", "gemini", "claude"]
            )
        )

    def get(self, name: str | None = None) -> AIProvider:
        target = name or self._default_name()
        if target not in PROVIDER_CLASSES:
            raise ValueError(f"Unknown AI provider: {target}")
        if target not in self._instances:
            self._instances[target] = PROVIDER_CLASSES[target]()
            logger.debug("Instantiated AI provider: %s", target)
        return self._instances[target]

    def get_fallbacks(self, exclude: str | None = None) -> list[AIProvider]:
        """Return available providers in configured fallback order, minus `exclude`."""
        result: list[AIProvider] = []
        for name in self._fallback_order():
            if name == exclude or name not in PROVIDER_CLASSES:
                continue
            try:
                provider = self.get(name)
            except Exception as exc:  # construction should not normally raise
                logger.warning("Could not instantiate provider %s: %s", name, exc)
                continue
            if provider.is_available():
                result.append(provider)
        return result

    def reset(self):
        """Clear cached instances (used in tests and after settings overrides)."""
        self._instances.clear()


ProviderRegistry = _ProviderRegistry()
