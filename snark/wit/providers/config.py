"""Strict loader for the AI providers file (``config/providers.yaml``).

The file is operator-trusted but parsed as hostile input: safe YAML only,
duplicate keys rejected at every depth, strict types, and errors that name the
provider key and field but never echo any configured value.
"""

import copy
import logging
import math
import re
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

PROVIDER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,49}$")
KEY_ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
MAX_MODEL_LENGTH = 100  # ResponseLog.model_name max_length

TOP_LEVEL_FIELDS = frozenset({"default", "fallback", "providers"})
COMMON_FIELDS = frozenset({"type", "model", "key", "price", "free"})
OPENAI_COMPATIBLE_FIELDS = COMMON_FIELDS | {"url", "extra_body"}
RESERVED_EXTRA_BODY_KEYS = frozenset(
    {"model", "messages", "stream", "stream_options", "max_tokens", "temperature", "n"}
)


class ProviderType(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    GEMINI = "gemini"
    CLAUDE = "claude"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    type: ProviderType
    model: str
    key_env: str | None = None
    url: str | None = None
    extra_body: Mapping[str, Any] | None = None
    price: tuple[float, float] | None = None
    free: bool = False


@dataclass(frozen=True)
class ProvidersConfig:
    default: str
    fallback: tuple[str, ...]
    providers: Mapping[str, ProviderSpec]


class ProviderConfigError(ImproperlyConfigured):
    """The providers file is missing or invalid. Messages never echo values."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys at every depth."""


def _construct_unique_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if isinstance(key, Hashable) and key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate key", key_node.start_mark
            )
        if isinstance(key, Hashable):
            seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: _construct_unique_mapping(loader, node, deep=True),
)


def load_providers_config(path: str | Path) -> ProvidersConfig:
    """Read and validate the providers file; raise ``ProviderConfigError``."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ProviderConfigError("AI providers file cannot be read") from None

    try:
        raw = yaml.load(text, Loader=_UniqueKeyLoader)  # noqa: S506 (SafeLoader)
    except (yaml.YAMLError, ValueError) as exc:
        # ValueError: a scalar that resolves to int/date but cannot be built;
        # its message quotes parts of the value, so it is reduced like the rest.
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        raise ProviderConfigError(
            f"AI providers file is not valid YAML{where}"
        ) from None
    except RecursionError:
        raise ProviderConfigError("AI providers file is nested too deeply") from None

    config = _build_config(raw)
    logger.info(
        "AI providers config loaded: default=%s providers=%d",
        config.default,
        len(config.providers),
    )
    return config


def _build_config(raw: Any) -> ProvidersConfig:
    if not isinstance(raw, dict):
        raise ProviderConfigError("AI providers file must be a mapping")
    if set(raw) - TOP_LEVEL_FIELDS:
        raise ProviderConfigError("AI providers file has an unknown top-level field")

    raw_providers = raw.get("providers")
    if not isinstance(raw_providers, dict) or not raw_providers:
        raise ProviderConfigError("'providers' must be a non-empty mapping")

    providers: dict[str, ProviderSpec] = {}
    for index, (name, raw_spec) in enumerate(raw_providers.items(), start=1):
        if not isinstance(name, str) or not PROVIDER_NAME_PATTERN.match(name):
            raise ProviderConfigError(f"provider #{index} has an invalid name")
        providers[name] = _build_spec(name, raw_spec)

    default = raw.get("default")
    if not isinstance(default, str) or default not in providers:
        raise ProviderConfigError("'default' must name a defined provider")

    raw_fallback = raw.get("fallback", [])
    if not isinstance(raw_fallback, list):
        raise ProviderConfigError("'fallback' must be a list")
    fallback: list[str] = []
    for entry in raw_fallback:
        if not isinstance(entry, str) or entry not in providers:
            raise ProviderConfigError("'fallback' must list only defined providers")
        if entry in fallback:
            raise ProviderConfigError("'fallback' must not repeat a provider")
        fallback.append(entry)

    return ProvidersConfig(
        default=default, fallback=tuple(fallback), providers=providers
    )


def _build_spec(name: str, raw: Any) -> ProviderSpec:
    def fail(field: str, problem: str) -> ProviderConfigError:
        return ProviderConfigError(f"provider '{name}': '{field}' {problem}")

    if not isinstance(raw, dict):
        raise ProviderConfigError(f"provider '{name}' must be a mapping")

    try:
        provider_type = ProviderType(raw.get("type"))
    except ValueError:
        raise fail("type", "must be openai_compatible, gemini or claude") from None

    openai_compatible = provider_type is ProviderType.OPENAI_COMPATIBLE
    allowed = OPENAI_COMPATIBLE_FIELDS if openai_compatible else COMMON_FIELDS
    if set(raw) - allowed:
        raise ProviderConfigError(f"provider '{name}' has an unsupported field")

    model = raw.get("model")
    if not isinstance(model, str) or not model or len(model) > MAX_MODEL_LENGTH:
        raise fail(
            "model",
            f"must be a non-empty string of at most {MAX_MODEL_LENGTH} characters",
        )

    key_env = raw.get("key")
    if key_env is not None and (
        not isinstance(key_env, str) or not KEY_ENV_PATTERN.match(key_env)
    ):
        raise fail("key", "must be an environment variable NAME such as MY_API_KEY")
    if key_env is None and not openai_compatible:
        raise fail("key", "is required")

    free = raw.get("free", False)
    if not isinstance(free, bool):
        raise fail("free", "must be true or false")
    price = _build_price(raw["price"]) if "price" in raw else None
    if "price" in raw and price is None:
        raise fail("price", "must be [input, output] finite non-negative numbers")
    if free and key_env is not None:
        raise fail("free", "is only for keyless providers")
    if free and price is not None:
        raise fail("free", "cannot be combined with 'price'")

    url = None
    extra_body = None
    if openai_compatible:
        url = _validate_url(raw.get("url"), has_key=key_env is not None, fail=fail)
        extra_body = _build_extra_body(raw.get("extra_body", {}), fail)

    return ProviderSpec(
        name=name,
        type=provider_type,
        model=model,
        key_env=key_env,
        url=url,
        extra_body=extra_body,
        price=price,
        free=free,
    )


def _build_price(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, list) or len(raw) != 2:
        return None
    values = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not math.isfinite(value) or value < 0:
            return None
        values.append(float(value))
    return values[0], values[1]


def _validate_url(raw: Any, has_key: bool, fail) -> str:
    if not isinstance(raw, str) or not raw:
        raise fail("url", "is required")
    try:
        parts = urlsplit(raw)
        parts.port  # noqa: B018 - raises ValueError on an invalid port
    except ValueError:
        raise fail("url", "is not a valid URL") from None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise fail("url", "must be an http(s) URL with a host")
    if parts.username is not None or parts.password is not None:
        raise fail("url", "must not contain credentials")
    if parts.query or parts.fragment:
        raise fail("url", "must not contain a query or fragment")
    if has_key and parts.scheme != "https":
        raise fail("url", "must use https when the provider has a key")
    return raw


def _build_extra_body(raw: Any, fail) -> Mapping[str, Any]:
    if not isinstance(raw, dict) or not all(isinstance(k, str) for k in raw):
        raise fail("extra_body", "must be a mapping with string keys")
    if RESERVED_EXTRA_BODY_KEYS & set(raw):
        raise fail("extra_body", "sets a field the provider controls")
    if not _is_json_clean(raw):
        raise fail("extra_body", "must contain only JSON values")
    return copy.deepcopy(raw)


def _is_json_clean(value: Any) -> bool:
    """True for str/int/finite float/bool/None and lists/str-key dicts of those.

    Recursive (cyclic) YAML anchors never get here: the loader's deep
    construction already rejects them as invalid YAML.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_clean(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_clean(item) for key, item in value.items()
        )
    return False
