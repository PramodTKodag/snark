from unittest.mock import MagicMock, patch

import pytest
from wit.models import ResponseLog
from wit.providers.base import AIResponse
from wit.providers.claude_provider import ClaudeProvider
from wit.providers.gemini_provider import GeminiProvider
from wit.providers.groq_provider import GroqProvider
from wit.services import WitService


class TestProviderTokenSplit:
    @patch("anthropic.Anthropic")
    def test_claude_splits_input_output(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        resp = MagicMock()
        resp.content = [MagicMock(text="hi")]
        resp.usage.input_tokens = 12
        resp.usage.output_tokens = 8
        client.messages.create.return_value = resp

        result = ClaudeProvider(api_key="k", model="m").generate("s", "u")

        assert result.input_tokens == 12
        assert result.output_tokens == 8
        assert result.tokens_used == 20

    @patch("groq.Groq")
    def test_groq_splits_input_output(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        resp = MagicMock()
        resp.choices = [
            MagicMock(finish_reason="stop", message=MagicMock(content="hi"))
        ]
        resp.usage.prompt_tokens = 30
        resp.usage.completion_tokens = 7
        client.chat.completions.create.return_value = resp

        result = GroqProvider(api_key="k", model="m").generate("s", "u")

        assert result.input_tokens == 30
        assert result.output_tokens == 7
        assert result.tokens_used == 37

    @patch("google.genai.Client")
    def test_gemini_splits_input_output(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        resp = MagicMock()
        resp.prompt_feedback = None
        resp.candidates = []
        resp.text = "hi"
        resp.usage_metadata.prompt_token_count = 40
        resp.usage_metadata.candidates_token_count = 9
        client.models.generate_content.return_value = resp

        result = GeminiProvider(api_key="k", model="m").generate("s", "u")

        assert result.input_tokens == 40
        assert result.output_tokens == 9
        assert result.tokens_used == 49


@pytest.mark.django_db
class TestServiceTokenSplit:
    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generate_persists_split_tokens(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        provider = MagicMock()
        provider.generate.return_value = AIResponse(
            text="No",
            tokens_used=30,
            model="m",
            provider="claude",
            latency_ms=5,
            input_tokens=12,
            output_tokens=18,
        )
        mock_registry.get.return_value = provider

        WitService.generate("say-no")

        log = ResponseLog.objects.get(persona=persona_no)
        assert log.input_tokens == 12
        assert log.output_tokens == 18
        assert log.tokens_used == 30
