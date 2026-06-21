from unittest.mock import MagicMock, patch

import pytest
from wit.providers.base import AIResponse, ContentFilterError, ProviderError
from wit.services import WitService


def _response(provider):
    return AIResponse(
        text="ok", tokens_used=1, model="m", provider=provider, latency_ms=1
    )


class TestGenerateWithFallback:
    @patch("wit.services.ProviderRegistry")
    def test_primary_success_skips_fallbacks(self, mock_registry):
        primary = MagicMock()
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
        primary.generate.side_effect = [
            ContentFilterError("blocked"),
            _response("groq"),
        ]
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
