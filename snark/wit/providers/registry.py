import logging
import threading
from dataclasses import dataclass

import decouple
from django.conf import settings

from .base import AIProvider
from .claude_provider import ClaudeProvider
from .config import ProvidersConfig, ProviderSpec, ProviderType, load_providers_config
from .gemini_provider import GeminiProvider
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

# Provider implementation for each configurable provider type.
PROVIDER_CLASSES: dict[ProviderType, type[AIProvider]] = {
    ProviderType.OPENAI_COMPATIBLE: OpenAICompatibleProvider,
    ProviderType.GEMINI: GeminiProvider,
    ProviderType.CLAUDE: ClaudeProvider,
}


@dataclass(frozen=True)
class _LoadedProviders:
    config: ProvidersConfig
    instances: dict[str, AIProvider]


def _build_provider(spec: ProviderSpec) -> AIProvider:
    """Instantiate one provider, resolving its API key from the environment.

    Keys are read here and handed straight to the provider; they never enter
    Django settings. A provider without a ``key`` is keyless and gets "".
    """
    api_key = decouple.config(spec.key_env, default="") if spec.key_env else ""
    if spec.key_env and not api_key:
        logger.warning(
            "Provider %s has no API key: set %s to enable it", spec.name, spec.key_env
        )
    return PROVIDER_CLASSES[spec.type](spec, api_key)


class _ProviderRegistry:
    """Builds and caches providers from the AI providers file.

    ``load()`` reads ``settings.AI_PROVIDERS_FILE``, validates it and builds
    every provider eagerly, so a bad file stops startup. ``reset()`` drops the
    cache; the next use reloads it lazily.
    """

    def __init__(self):
        self._loaded: _LoadedProviders | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        config = load_providers_config(settings.AI_PROVIDERS_FILE)
        instances = {
            name: _build_provider(spec) for name, spec in config.providers.items()
        }
        self._loaded = _LoadedProviders(config=config, instances=instances)

    def reset(self) -> None:
        """Drop loaded providers (used in tests)."""
        with self._lock:
            self._loaded = None

    def _ensure_loaded(self) -> _LoadedProviders:
        loaded = self._loaded
        if loaded is None:
            with self._lock:
                if self._loaded is None:
                    self.load()
                loaded = self._loaded
        return loaded

    @property
    def default_name(self) -> str:
        return self._ensure_loaded().config.default

    @property
    def fallback_names(self) -> list[str]:
        return list(self._ensure_loaded().config.fallback)

    def spec(self, name: str) -> ProviderSpec | None:
        return self._ensure_loaded().config.providers.get(name)

    def specs(self) -> dict[str, ProviderSpec]:
        return dict(self._ensure_loaded().config.providers)

    def get(self, name: str | None = None) -> AIProvider:
        loaded = self._ensure_loaded()
        target = name or loaded.config.default
        provider = loaded.instances.get(target)
        if provider is None:
            raise ValueError("Unknown AI provider")
        return provider

    def get_fallbacks(self, exclude: str | None = None) -> list[AIProvider]:
        """Return available providers in configured fallback order, minus `exclude`."""
        loaded = self._ensure_loaded()
        return [
            provider
            for name in loaded.config.fallback
            if name != exclude and (provider := loaded.instances[name]).is_available()
        ]


ProviderRegistry = _ProviderRegistry()
