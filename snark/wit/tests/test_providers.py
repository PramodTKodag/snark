from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from wit.providers.base import AIResponse, ContentFilterError, ProviderError
from wit.providers.claude_provider import ClaudeProvider
from wit.providers.gemini_provider import GeminiProvider
from wit.providers.groq_provider import GroqProvider
from wit.providers.registry import ProviderRegistry


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

        provider = ClaudeProvider(api_key="test-key", model="test-model")
        result = provider.generate("system", "user")

        assert isinstance(result, AIResponse)
        assert result.text == "Test response"
        assert result.tokens_used == 30
        assert result.provider == "claude"

    @patch("anthropic.Anthropic")
    def test_generate_raises_provider_error_on_api_failure(self, mock_anthropic_cls):
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="fail", request=MagicMock(), body=None
        )

        provider = ClaudeProvider(api_key="test-key")
        with pytest.raises(ProviderError):
            provider.generate("system", "user")


class TestProviderRegistry:
    def setup_method(self):
        ProviderRegistry.reset()

    def test_get_default_provider(self):
        provider = ProviderRegistry.get()
        assert provider.name == "groq"

    def test_get_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            ProviderRegistry.get("nonexistent")


class TestRegistrySettingsDriven:
    def teardown_method(self):
        ProviderRegistry.reset()

    @override_settings(AI_DEFAULT_PROVIDER="gemini")
    def test_default_provider_comes_from_settings(self):
        ProviderRegistry.reset()
        assert ProviderRegistry.get().name == "gemini"

    @override_settings(AI_PROVIDER_FALLBACK_ORDER=["claude", "groq", "gemini"])
    @patch("wit.providers.groq_provider.GroqProvider.is_available", return_value=True)
    @patch("wit.providers.gemini_provider.GeminiProvider.is_available", return_value=True)
    @patch("wit.providers.claude_provider.ClaudeProvider.is_available", return_value=True)
    def test_fallback_order_comes_from_settings(self, mock_claude_available, mock_gemini_available, mock_groq_available):
        ProviderRegistry.reset()
        names = [p.name for p in ProviderRegistry.get_fallbacks(exclude="claude")]
        assert names == ["groq", "gemini"]


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
        candidate.finish_reason = MagicMock()
        candidate.finish_reason.name = "PROHIBITED_CONTENT"
        blocked.candidates = [candidate]
        mock_client.models.generate_content.return_value = blocked

        provider = GeminiProvider(api_key="test-key", model="test-model")
        with pytest.raises(ContentFilterError):
            provider.generate("system", "user")
