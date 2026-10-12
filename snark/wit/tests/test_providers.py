import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings as django_settings
from django.test import override_settings
from wit.providers.base import AIResponse, ContentFilterError, ProviderError
from wit.providers.claude_provider import ClaudeProvider
from wit.providers.config import (
    ProviderConfigError,
    ProviderSpec,
    ProviderType,
    load_providers_config,
)
from wit.providers.gemini_provider import GeminiProvider
from wit.providers.openai_compatible import OpenAICompatibleProvider
from wit.providers.registry import ProviderRegistry
from wit.stats import provider_status

API_KEY = "sk-test-SECRET-1234567890"
SNARK_DIR = Path(__file__).resolve().parents[2]


def claude_spec(**overrides) -> ProviderSpec:
    fields = {
        "name": "claude",
        "type": ProviderType.CLAUDE,
        "model": "test-claude-model",
        "key_env": "ANTHROPIC_API_KEY",
    }
    fields.update(overrides)
    return ProviderSpec(**fields)


def gemini_spec(**overrides) -> ProviderSpec:
    fields = {
        "name": "gemini",
        "type": ProviderType.GEMINI,
        "model": "test-gemini-model",
        "key_env": "GEMINI_API_KEY",
    }
    fields.update(overrides)
    return ProviderSpec(**fields)


def write_providers_file(tmp_path, text) -> str:
    path = tmp_path / "providers.yaml"
    path.write_text(text)
    return str(path)


KEYLESS_FILE = """\
default: second
fallback: [second, first]
providers:
  first:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: m1
    free: true
  second:
    type: openai_compatible
    url: http://localhost:11435/v1
    model: m2
    free: true
"""

KEYED_FILE = """\
default: keyed
fallback: [keyed, local]
providers:
  keyed:
    type: openai_compatible
    url: https://llm.example.test/v1
    key: SNARK_TEST_KEYED_API_KEY
    model: m1
  local:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: m2
    free: true
"""


def test_default_and_fallback_come_from_file(tmp_path):
    path = write_providers_file(tmp_path, KEYLESS_FILE)
    with override_settings(AI_PROVIDERS_FILE=path):
        ProviderRegistry.reset()
        assert ProviderRegistry.default_name == "second"
        assert ProviderRegistry.fallback_names == ["second", "first"]
        assert ProviderRegistry.get().name == "second"
        assert [p.name for p in ProviderRegistry.get_fallbacks(exclude="second")] == [
            "first"
        ]


class TestClaudeProvider:
    @patch("anthropic.Anthropic")
    def test_generate_returns_ai_response(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_client.messages.create.return_value = mock_response

        provider = ClaudeProvider(claude_spec(), "test-key")
        result = provider.generate("system", "user")

        assert isinstance(result, AIResponse)
        assert result.text == "Test response"
        assert result.tokens_used == 30
        assert result.provider == "claude"
        assert result.model == "test-claude-model"
        assert mock_client.messages.create.call_args.kwargs["model"] == (
            "test-claude-model"
        )

    @patch("anthropic.Anthropic")
    def test_name_comes_from_spec(self, _mock_anthropic_cls):
        provider = ClaudeProvider(claude_spec(name="claude-fast"), "test-key")
        assert provider.name == "claude-fast"

    @patch("anthropic.Anthropic")
    def test_generate_raises_provider_error_on_api_failure(self, mock_anthropic_cls):
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="fail", request=MagicMock(), body=None
        )

        provider = ClaudeProvider(claude_spec(), "test-key")
        with pytest.raises(ProviderError):
            provider.generate("system", "user")

    @patch("anthropic.Anthropic")
    def test_generate_error_scrubs_key_and_drops_cause(
        self, mock_anthropic_cls, caplog
    ):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError(f"boom {API_KEY}")

        provider = ClaudeProvider(claude_spec(), API_KEY)
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                provider.generate("system", "user")

        assert API_KEY not in str(excinfo.value)
        assert API_KEY not in caplog.text
        assert excinfo.value.__cause__ is None
        assert excinfo.value.__suppress_context__ is True

    @patch("anthropic.Anthropic")
    def test_stream_error_scrubs_key(self, mock_anthropic_cls, caplog):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.stream.side_effect = RuntimeError(f"boom {API_KEY}")

        provider = ClaudeProvider(claude_spec(), API_KEY)
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                list(provider.generate_stream("system", "user"))

        assert API_KEY not in str(excinfo.value)
        assert API_KEY not in caplog.text

    @patch("anthropic.Anthropic")
    def test_bad_request_content_filter_raises_content_filter_error(
        self, mock_anthropic_cls
    ):
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.BadRequestError(
            message="Output blocked by content filtering policy",
            response=MagicMock(status_code=400, headers={}),
            body=None,
        )

        provider = ClaudeProvider(claude_spec(), "test-key")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")


class TestGeminiProvider:
    @patch("google.genai.Client")
    def test_built_from_spec(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        response = MagicMock()
        response.prompt_feedback = None
        response.candidates = []
        response.text = "hi"
        response.usage_metadata.prompt_token_count = 3
        response.usage_metadata.candidates_token_count = 4
        mock_client.models.generate_content.return_value = response

        provider = GeminiProvider(gemini_spec(name="gemini-pro"), "test-key")
        result = provider.generate("system", "user")

        assert provider.name == "gemini-pro"
        assert provider.model == "test-gemini-model"
        assert result.provider == "gemini-pro"
        assert result.model == "test-gemini-model"
        assert mock_client_cls.call_args.kwargs == {"api_key": "test-key"}
        assert mock_client.models.generate_content.call_args.kwargs["model"] == (
            "test-gemini-model"
        )

    @patch("google.genai.Client")
    def test_safety_thresholds_stay_explicit(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        response = MagicMock()
        response.prompt_feedback = None
        response.candidates = []
        response.text = "hi"
        mock_client.models.generate_content.return_value = response

        GeminiProvider(gemini_spec(), "test-key").generate("system", "user")

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert len(config.safety_settings) == 4
        assert {s.threshold.name for s in config.safety_settings} == {"BLOCK_ONLY_HIGH"}

    @patch("google.genai.Client")
    def test_generate_error_scrubs_key_and_drops_cause(self, mock_client_cls, caplog):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = RuntimeError(
            f"boom {API_KEY}"
        )

        provider = GeminiProvider(gemini_spec(), API_KEY)
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                provider.generate("system", "user")

        assert API_KEY not in str(excinfo.value)
        assert API_KEY not in caplog.text
        assert excinfo.value.__cause__ is None
        assert excinfo.value.__suppress_context__ is True

    @patch("google.genai.Client")
    def test_stream_error_scrubs_key(self, mock_client_cls, caplog):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content_stream.side_effect = RuntimeError(
            f"boom {API_KEY}"
        )

        provider = GeminiProvider(gemini_spec(), API_KEY)
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                list(provider.generate_stream("system", "user"))

        assert API_KEY not in str(excinfo.value)
        assert API_KEY not in caplog.text


class TestProviderRegistry:
    def test_get_unknown_provider_raises(self, tmp_path):
        path = write_providers_file(tmp_path, KEYLESS_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            with pytest.raises(ValueError, match="Unknown AI provider") as excinfo:
                ProviderRegistry.get("nonexistent")
        assert "nonexistent" not in str(excinfo.value)

    def test_get_returns_named_provider(self, tmp_path):
        path = write_providers_file(tmp_path, KEYLESS_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            assert ProviderRegistry.get("first").name == "first"
            assert ProviderRegistry.get("first") is ProviderRegistry.get("first")

    def test_spec_and_specs(self, tmp_path):
        path = write_providers_file(tmp_path, KEYLESS_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            assert ProviderRegistry.spec("first").model == "m1"
            assert ProviderRegistry.spec("missing") is None
            assert set(ProviderRegistry.specs()) == {"first", "second"}

    def test_fallbacks_skip_unavailable_and_excluded_primary(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("SNARK_TEST_KEYED_API_KEY", raising=False)
        path = write_providers_file(tmp_path, KEYED_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            # `keyed` has no key in the environment, so only `local` qualifies.
            assert [p.name for p in ProviderRegistry.get_fallbacks()] == ["local"]
            assert ProviderRegistry.get_fallbacks(exclude="local") == []

    def test_fallbacks_include_provider_once_its_key_is_set(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SNARK_TEST_KEYED_API_KEY", API_KEY)
        path = write_providers_file(tmp_path, KEYED_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            names = [p.name for p in ProviderRegistry.get_fallbacks(exclude="local")]
        assert names == ["keyed"]

    def test_keyless_provider_is_always_available(self, tmp_path):
        path = write_providers_file(tmp_path, KEYLESS_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            assert ProviderRegistry.get("first").is_available() is True

    def test_key_is_resolved_from_the_environment(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SNARK_TEST_KEYED_API_KEY", API_KEY)
        path = write_providers_file(tmp_path, KEYED_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            provider = ProviderRegistry.get("keyed")
        assert provider.is_available() is True
        assert provider._api_key == API_KEY
        assert not any(
            API_KEY == getattr(django_settings, name, None)
            for name in dir(django_settings)
        )

    def test_missing_key_leaves_provider_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SNARK_TEST_KEYED_API_KEY", raising=False)
        path = write_providers_file(tmp_path, KEYED_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            provider = ProviderRegistry.get("keyed")
        assert provider.is_available() is False
        with pytest.raises(ProviderError, match="SNARK_TEST_KEYED_API_KEY"):
            provider.generate("system", "user")

    def test_reset_reloads_lazily_from_the_current_setting(self, tmp_path):
        first = write_providers_file(tmp_path, KEYLESS_FILE)
        with override_settings(AI_PROVIDERS_FILE=first):
            assert ProviderRegistry.default_name == "second"
        other = tmp_path / "other.yaml"
        other.write_text(KEYLESS_FILE.replace("default: second", "default: first"))
        with override_settings(AI_PROVIDERS_FILE=str(other)):
            ProviderRegistry.reset()
            assert ProviderRegistry.default_name == "first"

    def test_bad_file_fails_load(self, tmp_path):
        path = write_providers_file(tmp_path, "default: nope\nproviders: {}\n")
        with override_settings(AI_PROVIDERS_FILE=path):
            with pytest.raises(ProviderConfigError):
                ProviderRegistry.load()

    def test_missing_file_fails_load(self, tmp_path):
        with override_settings(AI_PROVIDERS_FILE=str(tmp_path / "absent.yaml")):
            with pytest.raises(ProviderConfigError):
                ProviderRegistry.load()

    def test_startup_warning_names_only_the_env_var(
        self, tmp_path, monkeypatch, caplog
    ):
        monkeypatch.delenv("SNARK_TEST_KEYED_API_KEY", raising=False)
        monkeypatch.setenv("SNARK_TEST_OTHER_API_KEY", API_KEY)
        text = KEYED_FILE + (
            "  other:\n"
            "    type: openai_compatible\n"
            "    url: https://other.example.test/v1\n"
            "    key: SNARK_TEST_OTHER_API_KEY\n"
            "    model: m3\n"
        )
        path = write_providers_file(tmp_path, text)
        with override_settings(AI_PROVIDERS_FILE=path):
            with caplog.at_level(logging.DEBUG):
                ProviderRegistry.load()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "keyed" in message
        assert "SNARK_TEST_KEYED_API_KEY" in message
        assert API_KEY not in caplog.text

    def test_manage_check_fails_closed_on_bad_file_without_echoing_url(self, tmp_path):
        secret_url = "https://user:hunter2@leak.example.test/v1"
        path = write_providers_file(
            tmp_path,
            "default: bad\nproviders:\n  bad:\n    type: openai_compatible\n"
            f"    url: {secret_url}\n    model: m\n",
        )
        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=SNARK_DIR,
            env={**os.environ, "AI_PROVIDERS_FILE": path},
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "leak.example.test" not in output
        assert "hunter2" not in output


class TestShippedProvidersFile:
    def test_shipped_file_validates_and_matches_todays_behaviour(self):
        config = load_providers_config(
            Path(django_settings.BASE_DIR).parent / "config" / "providers.yaml"
        )

        assert config.default == "groq"
        assert config.fallback == ("groq", "gemini", "claude")
        ollama = config.providers["ollama"]
        assert ollama.key_env is None
        assert ollama.free is True
        assert "ollama" not in config.fallback
        assert config.providers["groq"].extra_body == {"reasoning_effort": "low"}

    def test_default_setting_points_at_the_shipped_file(self):
        expected = Path(django_settings.BASE_DIR).parent / "config" / "providers.yaml"
        assert Path(django_settings.AI_PROVIDERS_FILE) == expected


class TestProviderStatus:
    def test_lists_fallback_providers_with_default_flagged(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SNARK_TEST_KEYED_API_KEY", raising=False)
        path = write_providers_file(tmp_path, KEYED_FILE)
        with override_settings(AI_PROVIDERS_FILE=path):
            assert provider_status() == [
                {"name": "keyed", "configured": False, "is_default": True},
                {"name": "local", "configured": True, "is_default": False},
            ]

    def test_default_outside_fallback_is_appended(self, tmp_path):
        text = KEYLESS_FILE.replace("fallback: [second, first]", "fallback: [first]")
        path = write_providers_file(tmp_path, text)
        with override_settings(AI_PROVIDERS_FILE=path):
            assert [row["name"] for row in provider_status()] == ["first", "second"]
            assert provider_status()[1]["is_default"] is True


class TestProviderAvailability:
    def test_gemini_unavailable_without_key(self):
        provider = GeminiProvider(gemini_spec(), "")
        assert provider.is_available() is False
        with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
            provider.generate("system", "user")

    def test_claude_unavailable_without_key(self):
        provider = ClaudeProvider(claude_spec(), "")
        assert provider.is_available() is False
        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
            provider.generate("system", "user")

    def test_openai_compatible_unavailable_without_key(self):
        spec = ProviderSpec(
            name="groq",
            type=ProviderType.OPENAI_COMPATIBLE,
            model="m",
            key_env="GROQ_API_KEY",
            url="https://llm.example.test/v1",
        )
        provider = OpenAICompatibleProvider(spec, "")
        assert provider.is_available() is False
        with pytest.raises(ProviderError, match="GROQ_API_KEY"):
            provider.generate("system", "user")


class TestContentFilterDetection:
    @patch("google.genai.Client")
    def test_gemini_raises_content_filter_on_prompt_block(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        blocked = MagicMock()
        blocked.prompt_feedback = MagicMock(block_reason="SAFETY")
        blocked.candidates = []
        mock_client.models.generate_content.return_value = blocked

        provider = GeminiProvider(gemini_spec(), "test-key")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")

    @patch("google.genai.Client")
    def test_gemini_raises_content_filter_on_candidate_finish(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        blocked = MagicMock()
        blocked.prompt_feedback = None
        candidate = MagicMock()
        candidate.finish_reason = MagicMock()
        candidate.finish_reason.name = "PROHIBITED_CONTENT"
        blocked.candidates = [candidate]
        mock_client.models.generate_content.return_value = blocked

        provider = GeminiProvider(gemini_spec(), "test-key")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")
