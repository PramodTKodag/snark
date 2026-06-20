from unittest.mock import MagicMock, patch

import pytest

from wit.providers.base import AIResponse, ProviderError
from wit.providers.claude_provider import ClaudeProvider
from wit.providers.registry import ProviderRegistry


class TestClaudeProvider:
    @patch("wit.providers.claude_provider.anthropic.Anthropic")
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

    @patch("wit.providers.claude_provider.anthropic.Anthropic")
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
    def test_get_default_provider(self):
        provider = ProviderRegistry.get()
        assert provider.name == "claude"

    def test_get_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            ProviderRegistry.get("nonexistent")
