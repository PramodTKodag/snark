# snark Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the 16 audited issues in the snark API — single-sourced provider selection, working content-filter handling, privacy-compliant logging, immediate persona-cache invalidation, validated input, and a green, trustworthy test suite — without temporary workarounds.

**Architecture:** snark is a public, no-auth Django 5.1 / DRF service. Endpoint behavior is data-driven by `Persona` rows; all LLM calls go through the `wit/providers/` abstraction and the `WitService` orchestrator. This plan keeps that architecture and makes the half-wired parts real: provider selection becomes settings-driven (12-factor), providers detect their own safety blocks and degrade gracefully when unconfigured, and `ResponseLog` stops storing personal data.

**Tech Stack:** Python 3.12, Django 5.1.4, Django REST Framework, PostgreSQL, Redis (django-redis), Poetry, pytest / pytest-django.

## Global Constraints

- Python `>=3.12,<4.0`; Django `^5.1.4`; DRF `^3.15.1` — do not change these floors.
- **No authentication.** The service stays fully public; IP-based throttle only, `50/hour` via `WitAnonThrottle`.
- **Provider pattern is mandatory.** Never call `anthropic`, `groq`, or `google-genai` SDKs from views or services — only from `wit/providers/`.
- **Single source of truth for provider selection is Django settings** (read from env via `decouple.config`). After this work there is no `ProviderConfig` model and no `seed_providers` command.
- **Real code uses real data.** Dummy/fake values appear only in tests.
- **TDD strict:** every behavior change is a failing test first, then the minimal implementation, then green, then commit.
- **Naming:** self-explanatory names; classes `PascalCase`, functions/vars `snake_case`, settings `UPPER_SNAKE_CASE`.
- **Logging:** keep structured `logger` calls; never log secrets or raw IPs.
- Migrations are generated with `makemigrations`, never hand-edited unless the step says so.
- Tests require a reachable PostgreSQL (the `default` DATABASE) because most use `@pytest.mark.django_db`. Run the dev DB (`docker compose --profile dev up -d` or a local Postgres matching `.env`) before running the suite. Run tests with `cd snark && python -m pytest ...`.
- Branch: `hardening/snark-issues` (already created).

**Issue-to-task map** (audit numbers → tasks): #1 → T1; #4 → T2; #7,#8 → T3; #2 → T4; #3 → T5; #5 → T6; #6,#15 → T7; #16 → T8; #14 → T9; #9,#11 → T10; #10,#13 → T11; #12 → T1+T12.

---

### Task 1: Repair the stale test suite to a green baseline

The suite currently fails against the real code (wrong URLs, wrong slugs, wrong default provider, a count of 10 vs 28 personas). Fix it to reflect **current** behavior so later tasks can detect real regressions. This task changes only tests + the shared fixture.

**Files:**
- Modify: `snark/conftest.py`
- Modify: `snark/wit/tests/test_views.py`
- Modify: `snark/wit/tests/test_services.py`
- Modify: `snark/wit/tests/test_models.py`
- Modify: `snark/wit/tests/test_providers.py`
- Rewrite: `snark/wit/tests/test_seed_command.py`

**Interfaces:**
- Consumes: existing `Persona` model, `WitService.generate`, real URL names from `snark/wit/urls.py`, real slugs from `seed_personas.py`.
- Produces: fixtures `persona_no` (slug `"say-no"`) and `persona_roast` (slug `"roast"`); a green baseline for all later tasks.

- [ ] **Step 1: Update the shared fixtures to real slugs**

In `snark/conftest.py`, change the `persona_no` fixture's slug from `"no"` to `"say-no"` (leave `persona_roast` as `"roast"` — that slug is real):

```python
@pytest.fixture
def persona_no(db):
    return Persona.objects.create(
        slug="say-no",
        name="The Refusal Artist",
        system_prompt="You are a creative refusal generator.",
        rules=["Keep it short", "Be creative"],
        tone="witty",
        temperature=0.95,
        max_tokens=200,
        is_active=True,
    )
```

- [ ] **Step 2a: Replace class-level `@override_settings` with the pytest-django `settings` fixture**

`test_views.py` decorates plain pytest classes with `@override_settings(...)`, which Django 5.2 rejects at collection time ("Only subclasses of Django SimpleTestCase can be decorated with override_settings"). Convert both test classes to override settings inside their autouse `setup` fixture instead.

Remove the `from django.test import override_settings` import. Replace the `TestWitViews` class decorator + setup with:

```python
@pytest.mark.django_db
class TestWitViews:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        settings.REST_FRAMEWORK = {
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
            "DEFAULT_AUTHENTICATION_CLASSES": [],
            "DEFAULT_PERMISSION_CLASSES": [],
            "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        }
        self.client = APIClient()
```

Replace the `TestHealthViews` class decorator + setup with:

```python
@pytest.mark.django_db
class TestHealthViews:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        self.client = APIClient()
```

> NOTE: `settings` here is the pytest-django fixture (mutating it auto-reverts after each test). It coexists with `@patch(...)` method decorators — the patched arg comes first, fixtures resolve by name.

- [ ] **Step 2b: Fix the view tests to hit real URLs**

In `snark/wit/tests/test_views.py`, correct the endpoint paths to the ones registered in `snark/wit/urls.py`. Replace the five wrong paths:

```python
        resp = self.client.get("/v1/wit/say-no/")          # was /v1/wit/no/
        resp = self.client.get("/v1/wit/random-excuse/")   # was /v1/wit/excuse/
        resp = self.client.get("/v1/wit/corporate-jargon/")# was /v1/wit/corporate/
        resp = self.client.get("/v1/wit/commit-message/")  # was /v1/wit/commit/
        resp = self.client.get("/v1/wit/bug-blame/")       # was /v1/wit/blame/
        resp = self.client.get("/v1/wit/explain-like-im-5/", {"q": "kubernetes"})  # was /v1/wit/eli5/
```

Also fix the two required-`q` "missing" tests to the real paths:

```python
    def test_eli5_missing_q(self):
        resp = self.client.get("/v1/wit/explain-like-im-5/")
        assert resp.status_code == 400
```

(`worth-it` path is already correct.)

- [ ] **Step 3: Fix the service test slug**

In `snark/wit/tests/test_services.py`, the two tests that call `WitService.generate("no")` must use the fixture's real slug:

```python
        result = WitService.generate("say-no", ip_address="127.0.0.1")
```
```python
        result = WitService.generate("say-no")
```

- [ ] **Step 4: Fix the model test slug assertion**

In `snark/wit/tests/test_models.py`, update the `persona_no` slug assertion and the duplicate-slug test:

```python
    def test_create_persona(self, persona_no):
        assert persona_no.slug == "say-no"
        assert persona_no.name == "The Refusal Artist"
        assert persona_no.is_active is True

    def test_slug_unique(self, persona_no):
        with pytest.raises(Exception):
            Persona.objects.create(
                slug="say-no",
                name="Duplicate",
                system_prompt="dup",
                tone="test",
            )
```

- [ ] **Step 5: Fix the provider registry default-provider test**

In `snark/wit/tests/test_providers.py`, the current default is `groq` (not `claude`):

```python
    def test_get_default_provider(self):
        provider = ProviderRegistry.get()
        assert provider.name == "groq"
```

- [ ] **Step 6: Rewrite the seed-command test to be self-maintaining**

Replace the whole body of `snark/wit/tests/test_seed_command.py` so it derives the expected count from the command's own data and checks real slugs + idempotency:

```python
import pytest
from django.core.management import call_command

from wit.management.commands.seed_personas import PERSONAS
from wit.models import Persona


@pytest.mark.django_db
class TestSeedPersonas:
    def test_seed_creates_all_personas(self):
        call_command("seed_personas")
        assert Persona.objects.count() == len(PERSONAS)

    def test_seed_is_idempotent(self):
        call_command("seed_personas")
        call_command("seed_personas")
        assert Persona.objects.count() == len(PERSONAS)

    def test_seed_slugs_match_definitions(self):
        call_command("seed_personas")
        expected = {p["slug"] for p in PERSONAS}
        actual = set(Persona.objects.values_list("slug", flat=True))
        assert actual == expected

    def test_seed_slugs_are_unique(self):
        slugs = [p["slug"] for p in PERSONAS]
        assert len(slugs) == len(set(slugs))
```

- [ ] **Step 7: Run the full suite and confirm green**

Run: `cd snark && python -m pytest -v`
Expected: PASS (no failures, no errors). If a wit endpoint test still 404s, cross-check its path against `snark/wit/urls.py`.

- [ ] **Step 8: Commit**

```bash
git add snark/conftest.py snark/wit/tests/
git commit -m "test: repair stale test suite to reflect current routes, slugs, and defaults"
```

---

### Task 2: Make provider selection settings-driven (single source of truth)

Replace the registry's hardcoded `register(...)` order/default with values read from Django settings, and add per-provider model settings (fixing the latent "everything uses the Groq model" bug). Add an `is_available()` contract to the provider base so the registry can skip unconfigured providers (overridden per-provider in Task 3).

**Files:**
- Modify: `snark/base/settings.py:158-172`
- Modify: `snark/wit/providers/base.py`
- Rewrite: `snark/wit/providers/registry.py`
- Modify: `snark/wit/tests/test_providers.py`
- Modify: `.env.example`

**Interfaces:**
- Produces:
  - settings `AI_DEFAULT_PROVIDER: str`, `AI_PROVIDER_FALLBACK_ORDER: list[str]`, `GROQ_MODEL: str`, `GEMINI_MODEL: str`, `CLAUDE_MODEL: str`.
  - `AIProvider.is_available(self) -> bool` (default `True`).
  - `ProviderRegistry.get(name: str | None) -> AIProvider`, `ProviderRegistry.get_fallbacks(exclude: str | None) -> list[AIProvider]`, `ProviderRegistry.reset() -> None`.
- Consumes: provider classes `GroqProvider`, `GeminiProvider`, `ClaudeProvider`.

- [ ] **Step 1: Write failing tests for settings-driven selection**

Append to `snark/wit/tests/test_providers.py`:

```python
from django.test import override_settings


class TestRegistrySettingsDriven:
    def teardown_method(self):
        ProviderRegistry.reset()

    @override_settings(AI_DEFAULT_PROVIDER="gemini")
    def test_default_provider_comes_from_settings(self):
        ProviderRegistry.reset()
        assert ProviderRegistry.get().name == "gemini"

    @override_settings(AI_PROVIDER_FALLBACK_ORDER=["claude", "groq", "gemini"])
    def test_fallback_order_comes_from_settings(self):
        ProviderRegistry.reset()
        names = [p.name for p in ProviderRegistry.get_fallbacks(exclude="claude")]
        assert names == ["groq", "gemini"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd snark && python -m pytest wit/tests/test_providers.py::TestRegistrySettingsDriven -v`
Expected: FAIL (current registry ignores settings; default is the import-time `groq`).

- [ ] **Step 3: Add the `is_available` contract to the base**

In `snark/wit/providers/base.py`, add a concrete default method to `AIProvider` (after the abstract `health_check`):

```python
    def is_available(self) -> bool:
        """Whether this provider is configured and usable. Overridden per provider."""
        return True
```

- [ ] **Step 4: Add settings**

In `snark/base/settings.py`, replace the `# AI Provider Configuration` block (lines ~158-172) with:

```python
# AI Provider Configuration — settings are the single source of truth.
AI_DEFAULT_PROVIDER = config("AI_DEFAULT_PROVIDER", default="groq")
AI_PROVIDER_FALLBACK_ORDER = config(
    "AI_PROVIDER_FALLBACK_ORDER",
    default="groq,gemini,claude",
    cast=lambda v: [p.strip() for p in v.split(",") if p.strip()],
)
AI_DEFAULT_MAX_TOKENS = config("AI_DEFAULT_MAX_TOKENS", default=300, cast=int)

# Per-provider model identifiers (real model ids; override via env per deployment).
GROQ_MODEL = config("GROQ_MODEL", default="llama-3.3-70b-versatile")
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.0-flash")
CLAUDE_MODEL = config("CLAUDE_MODEL", default="claude-haiku-4-5-20251001")

# Per-provider API key env var names.
GROQ_API_KEY_ENV_VAR = config("GROQ_API_KEY_ENV_VAR", default="GROQ_API_KEY")
GEMINI_API_KEY_ENV_VAR = config("GEMINI_API_KEY_ENV_VAR", default="GEMINI_API_KEY")
ANTHROPIC_API_KEY_ENV_VAR = config(
    "ANTHROPIC_API_KEY_ENV_VAR", default="ANTHROPIC_API_KEY"
)
```

> NOTE: `AI_DEFAULT_MODEL` is intentionally removed — each provider now reads its own `*_MODEL` setting (Task 3 wires this). The old `claude-haiku-4-20250414` was not a real model id; `claude-haiku-4-5-20251001` is.

- [ ] **Step 5: Rewrite the registry to read settings**

Replace the entire contents of `snark/wit/providers/registry.py` with:

```python
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
        return list(getattr(settings, "AI_PROVIDER_FALLBACK_ORDER", ["groq", "gemini", "claude"]))

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
```

- [ ] **Step 6: Run the new + existing provider tests**

Run: `cd snark && python -m pytest wit/tests/test_providers.py -v`
Expected: PASS (settings-driven tests pass; `test_get_default_provider` still returns `groq`; `test_get_unknown_provider_raises` still matches "Unknown AI provider").

- [ ] **Step 7: Update `.env.example`**

In `.env.example`, replace the AI provider block with the new knobs:

```env
# ---- AI providers (settings are the single source of truth) ----
# Default provider and the fallback order tried on failure/content-filter.
AI_DEFAULT_PROVIDER=groq
AI_PROVIDER_FALLBACK_ORDER=groq,gemini,claude

# Per-provider model ids (override per deployment if needed).
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_MODEL=gemini-2.0-flash
CLAUDE_MODEL=claude-haiku-4-5-20251001

# Groq (free tier — get key at https://console.groq.com/keys)
GROQ_API_KEY=your-groq-api-key-here

# Gemini (optional — free tier if available in your region)
# GEMINI_API_KEY=your-gemini-api-key-here

# Anthropic (optional — requires paid credits)
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

- [ ] **Step 8: Commit**

```bash
git add snark/base/settings.py snark/wit/providers/base.py snark/wit/providers/registry.py snark/wit/tests/test_providers.py .env.example
git commit -m "feat: drive provider default/order/model from settings (single source of truth)"
```

---

### Task 3: Lazy, graceful provider initialization (no `api_key='missing'`, uniform imports)

Stop constructing SDK clients with a fake `"missing"` key. Each provider reads its own model setting, defers the SDK import uniformly, becomes unavailable (not crashing) when unconfigured, and raises a clear `ProviderError` if `generate()` is called while unavailable.

**Files:**
- Rewrite: `snark/wit/providers/groq_provider.py`
- Rewrite: `snark/wit/providers/gemini_provider.py`
- Rewrite: `snark/wit/providers/claude_provider.py`
- Modify: `snark/wit/tests/test_providers.py`

**Interfaces:**
- Consumes: settings `GROQ_MODEL`, `GEMINI_MODEL`, `CLAUDE_MODEL`, `*_API_KEY_ENV_VAR`; `AIProvider.is_available`.
- Produces: each provider overrides `is_available() -> bool`; `generate()` raises `ProviderError` when unavailable; constructors never raise on missing key or missing SDK.

- [ ] **Step 1: Write failing tests for graceful unavailability**

Append to `snark/wit/tests/test_providers.py`:

```python
from wit.providers.groq_provider import GroqProvider
from wit.providers.gemini_provider import GeminiProvider


class TestProviderAvailability:
    def test_groq_unavailable_without_key(self):
        provider = GroqProvider(api_key="")
        assert provider.is_available() is False
        with pytest.raises(ProviderError):
            provider.generate("system", "user")

    def test_gemini_unavailable_without_key(self):
        provider = GeminiProvider(api_key="")
        assert provider.is_available() is False
        with pytest.raises(ProviderError):
            provider.generate("system", "user")

    def test_claude_unavailable_without_key(self):
        provider = ClaudeProvider(api_key="")
        assert provider.is_available() is False
        with pytest.raises(ProviderError):
            provider.generate("system", "user")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_providers.py::TestProviderAvailability -v`
Expected: FAIL (today the constructors build a client with `"missing"` and `is_available` is the base `True`).

- [ ] **Step 3: Rewrite `groq_provider.py`**

Replace the entire file with:

```python
import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq chat-completions provider (OpenAI-compatible API)."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            from groq import Groq
        except ImportError:
            self._unavailable_reason = "groq package not installed"
            logger.warning("GroqProvider unavailable: %s", self._unavailable_reason)
            return

        env_var = getattr(settings, "GROQ_API_KEY_ENV_VAR", "GROQ_API_KEY")
        self._api_key = api_key if api_key is not None else os.environ.get(env_var, "")
        self._model = model or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        if not self._api_key:
            self._unavailable_reason = f"no API key (set {env_var})"
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
            raise ProviderError(f"Groq provider unavailable: {self._unavailable_reason}")

        start = time.monotonic()
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            logger.error("Groq API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Groq API call failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        if choice is not None and getattr(choice, "finish_reason", None) == "content_filter":
            logger.warning("Groq content filter triggered (finish_reason=content_filter)")
            raise ContentFilterError("Groq content filter blocked the response")

        latency_ms = int((time.monotonic() - start) * 1000)
        text = choice.message.content if choice else ""
        tokens_used = 0
        if response.usage:
            tokens_used = (response.usage.prompt_tokens or 0) + (
                response.usage.completion_tokens or 0
            )

        return AIResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
        )

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
```

- [ ] **Step 4: Rewrite `gemini_provider.py`**

Replace the entire file with:

```python
import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)

# Gemini candidate finish reasons that indicate a safety/content block.
_GEMINI_SAFETY_FINISH = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY"}


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
        self._model_name = model or getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

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
            raise ProviderError(f"Gemini provider unavailable: {self._unavailable_reason}")

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

    @staticmethod
    def _raise_if_blocked(response) -> None:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None and getattr(prompt_feedback, "block_reason", None):
            reason = getattr(prompt_feedback.block_reason, "name", str(prompt_feedback.block_reason))
            logger.warning("Gemini blocked prompt: %s", reason)
            raise ContentFilterError(f"Gemini blocked the prompt: {reason}")

        for candidate in (getattr(response, "candidates", None) or []):
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
```

- [ ] **Step 5: Rewrite `claude_provider.py`** (defer the SDK import like the others; keep the existing content-filter detection)

Replace the entire file with:

```python
import logging
import os
import time

from django.conf import settings

from .base import AIProvider, AIResponse, ContentFilterError, ProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = None
        self._unavailable_reason: str | None = None

        try:
            import anthropic
        except ImportError:
            self._unavailable_reason = "anthropic package not installed"
            logger.warning("ClaudeProvider unavailable: %s", self._unavailable_reason)
            return

        self._anthropic = anthropic
        env_var = getattr(settings, "ANTHROPIC_API_KEY_ENV_VAR", "ANTHROPIC_API_KEY")
        self._api_key = api_key if api_key is not None else os.environ.get(env_var, "")
        self._model = model or getattr(settings, "CLAUDE_MODEL", "claude-haiku-4-5-20251001")

        if not self._api_key:
            self._unavailable_reason = f"no API key (set {env_var})"
            logger.warning("ClaudeProvider unavailable: %s", self._unavailable_reason)
            return

        self._client = anthropic.Anthropic(api_key=self._api_key)
        logger.info("ClaudeProvider ready: model=%s", self._model)

    @property
    def name(self) -> str:
        return "claude"

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
            raise ProviderError(f"Claude provider unavailable: {self._unavailable_reason}")

        anthropic = self._anthropic
        start = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.BadRequestError as exc:
            if "content filtering" in str(exc).lower() or "blocked" in str(exc).lower():
                logger.warning("Claude content filter triggered: %s", exc)
                raise ContentFilterError(f"Claude content filter blocked response: {exc}") from exc
            logger.error("Claude bad request [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except anthropic.APIError as exc:
            logger.error("Claude API error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude API call failed: {exc}") from exc
        except Exception as exc:
            logger.error("Claude provider unexpected error [%s]: %s", type(exc).__name__, exc)
            raise ProviderError(f"Claude provider error: {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.content[0].text if response.content else ""
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return AIResponse(
            text=text,
            tokens_used=tokens,
            model=self._model,
            provider=self.name,
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
```

> NOTE: the existing Claude test patches `wit.providers.claude_provider.anthropic.Anthropic`. Because the import is now deferred, that patch target no longer exists. Step 6 updates that test.

- [ ] **Step 6: Update the existing Claude tests to the deferred-import patch target**

In `snark/wit/tests/test_providers.py`, change both `@patch("wit.providers.claude_provider.anthropic.Anthropic")` decorators to patch the SDK at its source (`anthropic.Anthropic`), which the deferred `import anthropic` resolves to:

```python
    @patch("anthropic.Anthropic")
    def test_generate_returns_ai_response(self, mock_anthropic_cls):
        ...

    @patch("anthropic.Anthropic")
    def test_generate_raises_provider_error_on_api_failure(self, mock_anthropic_cls):
        ...
```

- [ ] **Step 7: Run provider tests**

Run: `cd snark && python -m pytest wit/tests/test_providers.py -v`
Expected: PASS (availability tests pass; existing Claude tests still pass with the new patch target).

- [ ] **Step 8: Commit**

```bash
git add snark/wit/providers/ snark/wit/tests/test_providers.py
git commit -m "feat: lazy provider init with is_available(); per-provider models; uniform deferred imports"
```

---

### Task 4: Real content-filter detection for Groq and Gemini

The Groq/Gemini detection code landed in Task 3; this task proves it with tests so the `WitService` soften-and-retry path actually fires under the default provider.

**Files:**
- Modify: `snark/wit/tests/test_providers.py`

**Interfaces:**
- Consumes: `GroqProvider.generate`, `GeminiProvider.generate`, `ContentFilterError`.

- [ ] **Step 1: Write failing tests for content-filter detection**

Append to `snark/wit/tests/test_providers.py`:

```python
from wit.providers.base import ContentFilterError


class TestContentFilterDetection:
    @patch("groq.Groq")
    def test_groq_raises_content_filter_on_finish_reason(self, mock_groq_cls):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        blocked = MagicMock()
        blocked.choices = [MagicMock(finish_reason="content_filter")]
        blocked.usage = None
        mock_client.chat.completions.create.return_value = blocked

        provider = GroqProvider(api_key="test-key", model="test-model")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")

    @patch("google.genai.Client")
    def test_gemini_raises_content_filter_on_prompt_block(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        blocked = MagicMock()
        blocked.prompt_feedback = MagicMock(block_reason="SAFETY")
        blocked.candidates = []
        mock_client.models.generate_content.return_value = blocked

        provider = GeminiProvider(api_key="test-key", model="test-model")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")

    @patch("google.genai.Client")
    def test_gemini_raises_content_filter_on_candidate_finish(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        blocked = MagicMock()
        blocked.prompt_feedback = None
        candidate = MagicMock()
        candidate.finish_reason = MagicMock(name="finish")
        candidate.finish_reason.name = "PROHIBITED_CONTENT"
        blocked.candidates = [candidate]
        mock_client.models.generate_content.return_value = blocked

        provider = GeminiProvider(api_key="test-key", model="test-model")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")
```

- [ ] **Step 2: Run the tests**

Run: `cd snark && python -m pytest wit/tests/test_providers.py::TestContentFilterDetection -v`
Expected: PASS (detection implemented in Task 3). If a Gemini test errors on `.text`, confirm `_raise_if_blocked` runs before any `.text` access.

- [ ] **Step 3: Commit**

```bash
git add snark/wit/tests/test_providers.py
git commit -m "test: verify Groq/Gemini content-filter detection raises ContentFilterError"
```

---

### Task 5: Delete the unused `ProviderConfig` model and `seed_providers`

`ProviderConfig` is read by no runtime code. Remove the model, its admin, its seed command, its tests, and drop the DB table via migration. Update the docs/Makefile that mention `seed_providers`.

**Files:**
- Modify: `snark/wit/models.py:51-66`
- Modify: `snark/wit/admin.py`
- Delete: `snark/wit/management/commands/seed_providers.py`
- Modify: `snark/wit/tests/test_models.py`
- Create: `snark/wit/migrations/0002_delete_providerconfig.py` (generated)
- Modify: `Makefile:36-37`
- Modify: `CLAUDE.md`, `README.md`, `.claude/commands/seed.md`, `.claude/commands/add-provider.md`

**Interfaces:**
- Removes: `wit.models.ProviderConfig`, management command `seed_providers`.

- [ ] **Step 1: Remove the `ProviderConfig` tests**

In `snark/wit/tests/test_models.py`, delete the entire `TestProviderConfig` class (lines ~39-62) and remove `ProviderConfig` from the import on line 3:

```python
from wit.models import Persona, ResponseLog
```

- [ ] **Step 2: Remove the model**

In `snark/wit/models.py`, delete the entire `ProviderConfig` class (lines 51-66).

- [ ] **Step 3: Remove the admin registration**

In `snark/wit/admin.py`, remove `ProviderConfig` from the import and delete the `ProviderConfigAdmin` block, leaving:

```python
from django.contrib import admin

from .models import Persona, ResponseLog


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tone", "temperature", "is_active", "updated_at")
    list_filter = ("is_active", "tone")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display = ("persona", "tokens_used", "latency_ms", "provider_name", "created_at")
    list_filter = ("provider_name", "persona")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"
```

> NOTE: `ip_address` is also removed from `ResponseLogAdmin.list_display` here (it's removed from the model in Task 8; doing it now keeps admin import-valid between tasks).

- [ ] **Step 4: Delete the seed command**

```bash
git rm snark/wit/management/commands/seed_providers.py
```

- [ ] **Step 5: Generate the migration**

Run: `cd snark && python manage.py makemigrations wit`
Expected: creates `snark/wit/migrations/0002_delete_providerconfig.py` containing `migrations.DeleteModel(name="ProviderConfig")`. Open it and confirm it only deletes `ProviderConfig` (the `ResponseLogAdmin` change above is not a model change, so it won't appear).

- [ ] **Step 6: Update the Makefile `seed` target**

In `Makefile`, line 37, drop the `seed_providers` call:

```make
seed: ## Seed personas
	cd snark && python manage.py seed_personas
```

- [ ] **Step 7: Update docs that reference `seed_providers` / `ProviderConfig`**

- `CLAUDE.md`: in the architecture tree remove "seed_providers" from the management line; in "Adding a New Provider" replace step 4 ("Add to seed_providers.py") with: "Register the class in `providers/registry.py` `PROVIDER_CLASSES` and add `<NAME>_MODEL` / key env var settings"; in the Quick API Reference / models line remove `ProviderConfig`.
- `README.md` line ~150: change "seed_personas, seed_providers commands" to "seed_personas command".
- `.claude/commands/seed.md`: change "runs `seed_personas` then `seed_providers`" to "runs `seed_personas`".
- `.claude/commands/add-provider.md` step 4: replace the `seed_providers.py` instruction with the registry+settings instruction from the CLAUDE.md edit above.

- [ ] **Step 8: Run the full suite**

Run: `cd snark && python -m pytest -v`
Expected: PASS (no references to `ProviderConfig` remain). Sanity check: `grep -rn "ProviderConfig\|seed_providers" snark` returns nothing.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor: remove unused ProviderConfig model and seed_providers command"
```

---

### Task 6: Invalidate the persona cache on save/delete (signals)

Persona edits currently take up to an hour to apply (1h cache, no invalidation). Add signal receivers that delete the persona cache key on `post_save`/`post_delete`, and centralize the key so service and signals can't drift.

**Files:**
- Modify: `snark/wit/services.py`
- Create: `snark/wit/signals.py`
- Modify: `snark/wit/apps.py`
- Create/Modify: `snark/wit/tests/test_signals.py`

**Interfaces:**
- Produces: `wit.services.persona_cache_key(slug: str) -> str`; signal receiver `invalidate_persona_cache` connected in `WitConfig.ready()`.

- [ ] **Step 1: Write the failing test**

Create `snark/wit/tests/test_signals.py`:

```python
import pytest
from django.core.cache import cache

from wit.models import Persona
from wit.services import persona_cache_key


@pytest.mark.django_db
class TestPersonaCacheInvalidation:
    def test_save_clears_cache(self, persona_no):
        key = persona_cache_key(persona_no.slug)
        cache.set(key, persona_no, 3600)
        persona_no.name = "Renamed"
        persona_no.save()
        assert cache.get(key) is None

    def test_delete_clears_cache(self, persona_no):
        key = persona_cache_key(persona_no.slug)
        cache.set(key, persona_no, 3600)
        persona_no.delete()
        assert cache.get(key) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_signals.py -v`
Expected: FAIL — `ImportError` for `persona_cache_key` (and no invalidation yet).

- [ ] **Step 3: Centralize the cache key in the service**

In `snark/wit/services.py`, add a module-level helper (just below the constants, before the class) and use it in `_load_persona`:

```python
def persona_cache_key(slug: str) -> str:
    return f"persona:{slug}"
```

Then in `_load_persona`, replace `cache_key = f"persona:{slug}"` with:

```python
        cache_key = persona_cache_key(slug)
```

- [ ] **Step 4: Create the signals module**

Create `snark/wit/signals.py`:

```python
import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Persona
from .services import persona_cache_key

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Persona)
@receiver(post_delete, sender=Persona)
def invalidate_persona_cache(sender, instance, **kwargs):
    """Drop the cached persona so edits take effect immediately."""
    cache.delete(persona_cache_key(instance.slug))
    logger.debug("Invalidated persona cache for slug=%s", instance.slug)
```

- [ ] **Step 5: Connect the signals in `AppConfig.ready`**

In `snark/wit/apps.py`, add a `ready` method:

```python
from django.apps import AppConfig


class WitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wit"
    verbose_name = "Wit"

    def ready(self):
        from . import signals  # noqa: F401  (registers signal receivers)
```

- [ ] **Step 6: Run the test**

Run: `cd snark && python -m pytest wit/tests/test_signals.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add snark/wit/services.py snark/wit/signals.py snark/wit/apps.py snark/wit/tests/test_signals.py
git commit -m "feat: invalidate persona cache on save/delete via signals"
```

---

### Task 7: Make the `tone` field live and suppress the empty `Rules:` header

`Persona.tone` is stored but never used; the prompt always emits a `Rules:` header even with no rules. Fix both in `_build_prompt`.

**Files:**
- Modify: `snark/wit/services.py:128-151`
- Create/Modify: `snark/wit/tests/test_prompt_building.py`

**Interfaces:**
- Consumes: `Persona`, `WitService._build_prompt`.

- [ ] **Step 1: Write failing tests**

Create `snark/wit/tests/test_prompt_building.py`:

```python
import pytest

from wit.models import Persona
from wit.services import WitService


@pytest.mark.django_db
class TestBuildPrompt:
    def _persona(self, **overrides):
        defaults = dict(
            slug="t-persona",
            name="Tester",
            system_prompt="BASE PROMPT",
            rules=[],
            tone="deadpan",
            temperature=0.9,
            max_tokens=80,
            is_active=True,
        )
        defaults.update(overrides)
        return Persona.objects.create(**defaults)

    def test_tone_is_included(self):
        persona = self._persona(tone="deadpan")
        prompt = WitService._build_prompt(persona)
        assert "deadpan" in prompt

    def test_no_rules_header_when_empty(self):
        persona = self._persona(rules=[])
        prompt = WitService._build_prompt(persona)
        assert "Rules:" not in prompt

    def test_rules_header_present_when_rules_exist(self):
        persona = self._persona(rules=["Be brief"])
        prompt = WitService._build_prompt(persona)
        assert "Rules:" in prompt
        assert "- Be brief" in prompt

    def test_mood_override_included(self):
        persona = self._persona()
        prompt = WitService._build_prompt(persona, mood="sarcastic")
        assert "MOOD OVERRIDE" in prompt
        assert "sarcastic" in prompt
```

- [ ] **Step 2: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_prompt_building.py -v`
Expected: FAIL — `test_tone_is_included` (tone never added) and `test_no_rules_header_when_empty` (header always emitted) fail.

- [ ] **Step 3: Update `_build_prompt`**

In `snark/wit/services.py`, replace the body of `_build_prompt` (from `rules_text = ...` through the final `return`) with:

```python
        rules_text = "\n".join(f"- {r}" for r in persona.rules) if persona.rules else ""
        rules_block = f"\n\nRules:\n{rules_text}" if rules_text else ""

        tone_descriptor = f"\n\nPERSONA TONE: {persona.tone}." if persona.tone else ""

        mood_text = ""
        if mood:
            mood_text = (
                f"\n\nMOOD OVERRIDE: Deliver your response in a {mood} tone. "
                "This takes priority over your default tone."
            )

        anti_rep = ""
        if recent:
            samples = list(recent)
            anti_rep = (
                "\n\nIMPORTANT: Do NOT repeat or closely paraphrase any of these "
                "recent responses. Be completely original:\n"
                + "\n".join(f'- "{s[:80]}"' for s in samples)
            )

        tone_guide = (
            "\n\nTONE: Use simple, everyday language. Short sentences. "
            "No fancy words, no jargon, no filler. Write like you're texting a friend."
        )
        return (
            f"{persona.system_prompt}{tone_descriptor}{mood_text}"
            f"{tone_guide}{rules_block}{anti_rep}"
        )
```

(Keep the existing `recent = (...)` query at the top of the method unchanged.)

- [ ] **Step 4: Run the tests**

Run: `cd snark && python -m pytest wit/tests/test_prompt_building.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add snark/wit/services.py snark/wit/tests/test_prompt_building.py
git commit -m "feat: use persona.tone in prompt and omit empty Rules header"
```

---

### Task 8: Stop storing client IP (privacy / GDPR)

The raw IP in `ResponseLog` is personal data used by no runtime code (rate-limiting is the ephemeral DRF throttle). Remove the field, its index, and all writers.

**Files:**
- Modify: `snark/wit/models.py:33,44`
- Modify: `snark/wit/services.py`
- Modify: `snark/wit/views.py`
- Modify: `snark/wit/tests/test_services.py`
- Create: `snark/wit/migrations/0003_remove_responselog_ip_address.py` (generated)

**Interfaces:**
- Changes: `WitService.generate(slug, user_input="", mood=None)` — the `ip_address` parameter is removed. `BaseWitView` no longer has `get_client_ip`.

- [ ] **Step 1: Write the failing test for the new signature**

In `snark/wit/tests/test_services.py`, update `test_generate_creates_response_log` to call without `ip_address` and assert the field is gone:

```python
        result = WitService.generate("say-no")

        assert result["response"] == "No thanks"
        assert result["persona"] == "The Refusal Artist"
        assert result["cached"] is False
        assert ResponseLog.objects.filter(persona=persona_no).count() == 1
        assert not hasattr(ResponseLog.objects.first(), "ip_address")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_services.py::TestWitService::test_generate_creates_response_log -v`
Expected: FAIL — `ResponseLog` still has `ip_address`.

- [ ] **Step 3: Remove the model field and its index**

In `snark/wit/models.py`, delete line 33 (`ip_address = ...`) and the IP index in `Meta.indexes`, leaving:

```python
    class Meta:
        db_table = "response_logs"
        indexes = [
            models.Index(fields=["persona", "-created_at"]),
        ]
```

- [ ] **Step 4: Remove the `ip_address` parameter and writer in the service**

In `snark/wit/services.py`, change the `generate` signature and the `ResponseLog.objects.create(...)` call:

```python
    @staticmethod
    def generate(slug: str, user_input: str = "", mood: str | None = None) -> dict:
```

Remove the `ip_address=ip_address,` line from the `ResponseLog.objects.create(...)` block.

- [ ] **Step 5: Remove IP collection from the view**

In `snark/wit/views.py`, delete the `get_client_ip` method (lines 68-69) and remove the `ip_address=self.get_client_ip(request),` argument from the `WitService.generate(...)` call in `handle_generate`.

> NOTE: `handle_generate` is rewritten more thoroughly in Task 10; this step only removes the IP argument so the suite stays green between tasks.

- [ ] **Step 6: Generate the migration**

Run: `cd snark && python manage.py makemigrations wit`
Expected: creates `snark/wit/migrations/0003_remove_responselog_ip_address.py` with `RemoveIndex` + `RemoveField(model_name="responselog", name="ip_address")`. Open and confirm.

- [ ] **Step 7: Run the suite**

Run: `cd snark && python -m pytest -v`
Expected: PASS. Sanity: `grep -rn "ip_address\|get_client_ip" snark` returns nothing (except the new migration, which references the removal).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: stop persisting client IP in ResponseLog (privacy/GDPR)"
```

---

### Task 9: Add CORS support for the public API

The API is public with no CORS headers, so browsers from other origins are blocked. Add `django-cors-headers`, defaulting to allow-all (no credentials, no cookies), env-overridable.

**Files:**
- Modify: `pyproject.toml`
- Modify: `snark/base/settings.py`
- Modify: `.env.example`
- Create: `snark/wit/tests/test_cors.py`

**Interfaces:**
- Produces: `corsheaders` in `INSTALLED_APPS` + `MIDDLEWARE`; settings `CORS_ALLOW_ALL_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`.

- [ ] **Step 1: Add the dependency**

Run: `poetry add django-cors-headers`
(If Poetry is unavailable in the environment, add `django-cors-headers = "^4.4.0"` to `[tool.poetry.dependencies]` in `pyproject.toml` and `pip install django-cors-headers`.)

- [ ] **Step 2: Write the failing test**

Create `snark/wit/tests/test_cors.py`:

```python
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCors:
    @patch("wit.views.WitService.generate")
    def test_cors_header_present_for_cross_origin_request(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        client = APIClient()
        resp = client.get("/v1/wit/say-no/", HTTP_ORIGIN="https://example.com")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
```

- [ ] **Step 3: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_cors.py -v`
Expected: FAIL — no CORS header.

- [ ] **Step 4: Register the app and middleware**

In `snark/base/settings.py`, add `"corsheaders",` to `INSTALLED_APPS` (after `"drf_spectacular_sidecar",`). In `MIDDLEWARE`, insert `"corsheaders.middleware.CorsMiddleware",` immediately after `"django.middleware.security.SecurityMiddleware",` and before `"whitenoise.middleware.WhiteNoiseMiddleware",`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

- [ ] **Step 5: Add CORS settings**

In `snark/base/settings.py`, after the `SPECTACULAR_SETTINGS` block (end of file), add:

```python
# CORS — public, read-only, no-credential API. Allow all origins by default;
# restrict per deployment by setting CORS_ALLOW_ALL_ORIGINS=False and listing
# CORS_ALLOWED_ORIGINS.
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)
CORS_ALLOW_CREDENTIALS = False
```

- [ ] **Step 6: Document in `.env.example`**

Append to `.env.example`:

```env
# ---- CORS ----
# Public API: allow all origins by default. To restrict, set False and list origins.
CORS_ALLOW_ALL_ORIGINS=True
# CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

- [ ] **Step 7: Run the test**

Run: `cd snark && python -m pytest wit/tests/test_cors.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml poetry.lock snark/base/settings.py .env.example snark/wit/tests/test_cors.py
git commit -m "feat: add CORS support (allow-all default for public API)"
```

(If `poetry.lock` was not regenerated, omit it from the `git add`.)

---

### Task 10: Structured error codes + query-parameter validation

Give error responses a stable machine-readable `code` (without removing the existing `error` string), and replace the unused `WitInputSerializer` + manual parsing with a real `WitQuerySerializer` used by `BaseWitView`. Move `ALLOWED_MOODS` to a shared constants module so the serializer and service agree.

**Files:**
- Create: `snark/wit/constants.py`
- Modify: `snark/wit/services.py`
- Modify: `snark/wit/serializers.py`
- Modify: `snark/wit/views.py`
- Modify: `snark/wit/tests/test_views.py`

**Interfaces:**
- Produces: `wit.constants.ALLOWED_MOODS: frozenset[str]`; `WitQuerySerializer` (fields `q`, `mood`); error bodies `{"error": str, "code": str}` with codes `invalid_request` (400), `persona_not_found` (404), `provider_unavailable` (503), `internal_error` (500).
- Consumes: `WitService.generate(slug, user_input="", mood=None)` (from Task 8).

- [ ] **Step 1: Write failing tests**

Append to `snark/wit/tests/test_views.py`, inside `TestWitViews`:

```python
    @patch("wit.views.WitService.generate")
    def test_error_code_on_provider_failure(self, mock_gen):
        from wit.providers.base import ProviderError
        mock_gen.side_effect = ProviderError("boom")
        resp = self.client.get("/v1/wit/say-no/")
        assert resp.status_code == 503
        assert resp.json()["code"] == "provider_unavailable"

    @patch("wit.views.WitService.generate")
    def test_error_code_on_persona_not_found(self, mock_gen):
        from wit.services import PersonaNotFoundError
        mock_gen.side_effect = PersonaNotFoundError("nope")
        resp = self.client.get("/v1/wit/say-no/")
        assert resp.status_code == 404
        assert resp.json()["code"] == "persona_not_found"

    def test_invalid_mood_is_rejected(self):
        resp = self.client.get("/v1/wit/say-no/", {"mood": "not-a-real-mood"})
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    @patch("wit.views.WitService.generate")
    def test_valid_mood_is_passed_through(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        resp = self.client.get("/v1/wit/say-no/", {"mood": "sarcastic"})
        assert resp.status_code == 200
        assert mock_gen.call_args.kwargs["mood"] == "sarcastic"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd snark && python -m pytest wit/tests/test_views.py::TestWitViews -k "error_code or mood" -v`
Expected: FAIL — responses have no `code`; invalid mood is silently ignored (200, not 400).

- [ ] **Step 3: Create the shared constants module**

Create `snark/wit/constants.py`:

```python
# Allowed mood overrides accepted by wit endpoints.
ALLOWED_MOODS = frozenset(
    {
        "sarcastic", "angry", "funny", "sad", "excited", "dramatic",
        "passive-aggressive", "philosophical", "wholesome", "unhinged",
        "dry", "chaotic", "chill", "spicy", "deadpan",
    }
)
```

- [ ] **Step 4: Use the shared constant in the service**

In `snark/wit/services.py`, remove the local `ALLOWED_MOODS = frozenset({...})` definition and import it instead:

```python
from .constants import ALLOWED_MOODS
```

(Leave `PERSONA_CACHE_TTL`, `RESPONSE_CACHE_TTL`, `ANTI_REPETITION_COUNT` as they are. The `generate` method's `if mood and mood not in ALLOWED_MOODS: mood = None` line stays — it's a harmless second guard.)

- [ ] **Step 5: Replace the serializer**

In `snark/wit/serializers.py`, replace `WitInputSerializer` with `WitQuerySerializer`:

```python
from rest_framework import serializers

from .constants import ALLOWED_MOODS


class WitResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    persona = serializers.CharField()
    cached = serializers.BooleanField()


class WitQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")
    mood = serializers.ChoiceField(
        choices=sorted(ALLOWED_MOODS), required=False, allow_blank=True
    )


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    service = serializers.CharField()
    version = serializers.CharField()
    components = serializers.DictField()
```

- [ ] **Step 6: Rewrite `BaseWitView` to validate and emit codes**

In `snark/wit/views.py`, update the serializer import and replace the entire `BaseWitView` class (lines 61-103). New import line:

```python
from .serializers import HealthResponseSerializer, WitQuerySerializer, WitResponseSerializer
```

New class:

```python
class BaseWitView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WitAnonThrottle]

    def handle_generate(self, request, slug, user_input=None):
        params = WitQuerySerializer(data=request.query_params)
        if not params.is_valid():
            return Response(
                {
                    "error": "Invalid query parameters",
                    "code": "invalid_request",
                    "details": params.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = params.validated_data.get("q", "")
        mood = params.validated_data.get("mood") or None
        effective_input = user_input if user_input is not None else query

        try:
            result = WitService.generate(slug=slug, user_input=effective_input, mood=mood)
            return Response(result, status=status.HTTP_200_OK)
        except PersonaNotFoundError:
            return Response(
                {"error": f"Persona '{slug}' not found", "code": "persona_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProviderError as exc:
            logger.error("ProviderError for slug=%s: %s", slug, exc, exc_info=True)
            return Response(
                {"error": "AI service temporarily unavailable", "code": "provider_unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected error for slug=%s: %s", slug, exc)
            return Response(
                {"error": "Internal server error", "code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

> NOTE: This removes `get_user_input` and `MAX_INPUT_LENGTH` (now owned by the serializer) and `get_client_ip` (removed in Task 8). The required-`q` views (e.g. `WorthItView`) already read `q` themselves and pass `user_input=q`, then `handle_generate` validates and uses it — keep those views unchanged. `RoastView` passes `user_input=sanitized` — unchanged.

- [ ] **Step 7: Run the view tests**

Run: `cd snark && python -m pytest wit/tests/test_views.py -v`
Expected: PASS (new error-code and mood tests pass; existing endpoint tests still pass — `q`/`mood` absent validates fine).

- [ ] **Step 8: Run the full suite**

Run: `cd snark && python -m pytest -v`
Expected: PASS. Sanity: `grep -rn "WitInputSerializer\|get_client_ip\|get_user_input" snark` returns nothing.

- [ ] **Step 9: Commit**

```bash
git add snark/wit/constants.py snark/wit/services.py snark/wit/serializers.py snark/wit/views.py snark/wit/tests/test_views.py
git commit -m "feat: validate query params and return structured error codes"
```

---

### Task 11: Remove unused dependencies; document the auth-stack decision

Remove the two genuinely-unused dependencies and record why the Django auth/session apps stay (they're required by the admin used to manage personas).

**Files:**
- Modify: `pyproject.toml`
- Modify: `snark/base/settings.py`

**Interfaces:** none.

- [ ] **Step 1: Remove unused dependencies**

Run: `poetry remove django-ratelimit httpx`
(If Poetry is unavailable, delete the `django-ratelimit = "^4.1.0"` and `httpx = "^0.27.0"` lines from `[tool.poetry.dependencies]` in `pyproject.toml`.)

- [ ] **Step 2: Verify they were unused**

Run: `grep -rn "ratelimit\|httpx" snark`
Expected: no matches.

- [ ] **Step 3: Document the auth-stack decision (#13)**

In `snark/base/settings.py`, add a comment above `INSTALLED_APPS` explaining the intentional retention:

```python
# NOTE: django.contrib.auth/sessions/messages are retained intentionally — they
# are required by the Django admin, which operators use to manage Persona rows.
# The public API itself uses no authentication (DEFAULT_AUTHENTICATION_CLASSES=[]).
INSTALLED_APPS = [
```

- [ ] **Step 4: Run the full suite**

Run: `cd snark && python -m pytest -v`
Expected: PASS (nothing imported these packages).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock snark/base/settings.py
git commit -m "chore: remove unused deps (django-ratelimit, httpx); document auth-stack retention"
```

(Omit `poetry.lock` if not regenerated.)

---

### Task 12: Coverage hardening — fallback chain and throttle

Fill the highest-value gaps the audit named: the provider fallback orchestration and the rate-limit throttle.

**Files:**
- Create: `snark/wit/tests/test_fallback.py`
- Create: `snark/wit/tests/test_throttle.py`

**Interfaces:**
- Consumes: `WitService._generate_with_fallback`, `ProviderRegistry`, `WitAnonThrottle`.

- [ ] **Step 1: Write the fallback-chain tests**

Create `snark/wit/tests/test_fallback.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from wit.providers.base import AIResponse, ContentFilterError, ProviderError
from wit.services import WitService


def _response(provider):
    return AIResponse(text="ok", tokens_used=1, model="m", provider=provider, latency_ms=1)


class TestGenerateWithFallback:
    @patch("wit.services.ProviderRegistry")
    def test_primary_success_skips_fallbacks(self, mock_registry):
        primary = MagicMock(name="primary")
        primary.name = "groq"
        primary.generate.return_value = _response("groq")
        mock_registry.get.return_value = primary

        result = WitService._generate_with_fallback("sys", "user", 0.9, 80)

        assert result.provider == "groq"
        mock_registry.get_fallbacks.assert_not_called()

    @patch("wit.services.ProviderRegistry")
    def test_content_filter_triggers_softened_retry(self, mock_registry):
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = [ContentFilterError("blocked"), _response("groq")]
        mock_registry.get.return_value = primary

        result = WitService._generate_with_fallback("sys", "user", 0.9, 80)

        assert result.provider == "groq"
        assert primary.generate.call_count == 2
        # The retry softens the prompt and lowers temperature.
        retry_kwargs = primary.generate.call_args_list[1].kwargs
        assert retry_kwargs["temperature"] == pytest.approx(0.7)
        assert "safe for all audiences" in retry_kwargs["system_prompt"]

    @patch("wit.services.ProviderRegistry")
    def test_provider_error_falls_back_to_next(self, mock_registry):
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = ProviderError("down")
        fallback = MagicMock()
        fallback.name = "gemini"
        fallback.generate.return_value = _response("gemini")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = [fallback]

        result = WitService._generate_with_fallback("sys", "user", 0.9, 80)

        assert result.provider == "gemini"

    @patch("wit.services.ProviderRegistry")
    def test_all_providers_fail_raises(self, mock_registry):
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = ProviderError("down")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = []

        with pytest.raises(ProviderError):
            WitService._generate_with_fallback("sys", "user", 0.9, 80)
```

- [ ] **Step 2: Run the fallback tests**

Run: `cd snark && python -m pytest wit/tests/test_fallback.py -v`
Expected: PASS (these characterize existing behavior in `_generate_with_fallback`). If `test_content_filter_triggers_softened_retry` fails on temperature, confirm the retry uses `max(temperature - 0.2, 0.3)` → `0.7` for input `0.9`.

- [ ] **Step 3: Write the throttle test**

Create `snark/wit/tests/test_throttle.py`:

```python
from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestThrottle:
    @patch("wit.views.WitService.generate")
    def test_anonymous_requests_throttled_after_limit(self, mock_gen, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        cache.clear()
        client = APIClient()

        statuses = [client.get("/v1/wit/say-no/").status_code for _ in range(51)]

        assert statuses.count(200) == 50
        assert statuses[-1] == 429
```

> NOTE: uses the pytest-django `settings` fixture (not the class-level `@override_settings` decorator, which Django 5.2 rejects on plain pytest classes). It does NOT override `REST_FRAMEWORK`, so the per-view `WitAnonThrottle` (50/hour) stays active. LocMemCache backs the throttle counter; `cache.clear()` isolates the test.

- [ ] **Step 4: Run the throttle test**

Run: `cd snark && python -m pytest wit/tests/test_throttle.py -v`
Expected: PASS — 50 × 200 then 429.

- [ ] **Step 5: Run the entire suite with coverage**

Run: `cd snark && python -m pytest --cov=wit --cov-report=term-missing -v`
Expected: PASS. Review the coverage report; `services.py`, `registry.py`, and the providers should show materially higher coverage than baseline.

- [ ] **Step 6: Commit**

```bash
git add snark/wit/tests/test_fallback.py snark/wit/tests/test_throttle.py
git commit -m "test: cover provider fallback chain and rate-limit throttle"
```

---

## Final Verification (run after all tasks)

- [ ] `cd snark && python -m pytest -v` → all green.
- [ ] `make lint` → clean (or `cd snark && flake8 .`).
- [ ] `make format` then re-run tests (black/isort may reflow new files).
- [ ] `cd snark && python manage.py makemigrations --check --dry-run` → "No changes detected" (model and migrations are in sync).
- [ ] `grep -rn "ProviderConfig\|seed_providers\|ip_address\|get_client_ip\|WitInputSerializer\|AI_DEFAULT_MODEL" snark` → only expected references (migrations describing removals).
- [ ] Manual smoke (optional, needs DB + a real provider key): `make seed && make up`, then `curl localhost:8100/v1/wit/say-no/` and `curl "localhost:8100/v1/wit/say-no/?mood=bogus"` (expect `400 invalid_request`).

## Self-Review Notes (author)

- **Spec coverage:** every audit issue maps to a task (see issue-to-task map). #13 is resolved as a documented intentional decision (Task 11), not a code removal, because the admin requires the auth stack.
- **Type consistency:** `WitService.generate` signature change (drop `ip_address`) is applied in Task 8 and consumed in Task 10's `handle_generate`; `persona_cache_key` defined in Task 6 and reused by signals; `ALLOWED_MOODS` moves to `constants.py` in Task 10 and is imported by both service and serializer; `is_available()` added to base in Task 2 and overridden per-provider in Task 3.
- **Ordering:** Task 1 establishes green baseline first; model-deleting tasks (5, 8) each generate exactly one migration (0002, 0003) to keep history clean and reviewable.
