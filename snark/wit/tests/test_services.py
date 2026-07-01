import logging
from unittest.mock import MagicMock, patch

import pytest
from wit.models import ResponseLog
from wit.providers.base import AIResponse
from wit.services import PersonaNotFoundError, WitService


@pytest.mark.django_db
class TestWitService:
    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generate_creates_response_log(self, mock_cache, mock_registry, persona_no):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.generate.return_value = AIResponse(
            text="No thanks",
            tokens_used=15,
            model="test-model",
            provider="claude",
            latency_ms=50,
        )
        mock_registry.get.return_value = mock_provider

        result = WitService.generate("say-no")

        assert result["response"] == "No thanks"
        assert result["persona"] == "The Refusal Artist"
        assert result["cached"] is False
        assert ResponseLog.objects.filter(persona=persona_no).count() == 1
        assert "ip_address" not in [f.name for f in ResponseLog._meta.get_fields()]

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generate_redacts_input_by_default(
        self, mock_cache, mock_registry, persona_no, settings
    ):
        settings.LOG_INPUT_MODE = "redacted"
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.generate.return_value = AIResponse(
            text="No thanks",
            tokens_used=15,
            model="test-model",
            provider="claude",
            latency_ms=50,
        )
        mock_registry.get.return_value = mock_provider

        WitService.generate("say-no", user_input="reach me at a@b.com")

        log = ResponseLog.objects.get(persona=persona_no)
        assert log.input_text == "reach me at [email]"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generate_stores_raw_input_when_opted_in(
        self, mock_cache, mock_registry, persona_no, settings
    ):
        settings.LOG_INPUT_MODE = "raw"
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.generate.return_value = AIResponse(
            text="No thanks",
            tokens_used=15,
            model="test-model",
            provider="claude",
            latency_ms=50,
        )
        mock_registry.get.return_value = mock_provider

        WitService.generate("say-no", user_input="reach me at a@b.com")

        log = ResponseLog.objects.get(persona=persona_no)
        assert log.input_text == "reach me at a@b.com"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generate_emits_generation_log(
        self, mock_cache, mock_registry, persona_no, settings, caplog
    ):
        settings.PROVIDER_TOKEN_COST = "claude:1:3"
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.generate.return_value = AIResponse(
            text="No thanks",
            tokens_used=20,
            model="test-model",
            provider="claude",
            latency_ms=50,
            input_tokens=8,
            output_tokens=12,
        )
        mock_registry.get.return_value = mock_provider

        with caplog.at_level(logging.INFO, logger="wit.services"):
            WitService.generate("say-no")

        records = [
            r for r in caplog.records if getattr(r, "event", None) == "generation"
        ]
        assert len(records) == 1
        record = records[0]
        assert record.levelname == "INFO"
        assert record.getMessage() == "generation"
        assert record.persona == "say-no"
        assert record.provider == "claude"
        assert record.model == "test-model"
        assert record.tokens == 20
        assert record.input_tokens == 8
        assert record.output_tokens == 12
        assert record.latency_ms == 50
        assert record.streamed is False
        # 8 input * $1/1M + 12 output * $3/1M
        assert hasattr(record, "cost_usd")
        assert record.cost_usd == pytest.approx(4.4e-5)

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_generation_log_excludes_raw_input(
        self, mock_cache, mock_registry, persona_no, caplog
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.generate.return_value = AIResponse(
            text="No thanks",
            tokens_used=15,
            model="test-model",
            provider="claude",
            latency_ms=50,
        )
        mock_registry.get.return_value = mock_provider

        with caplog.at_level(logging.INFO, logger="wit.services"):
            WitService.generate("say-no", user_input="my secret is hunter2")

        records = [
            r for r in caplog.records if getattr(r, "event", None) == "generation"
        ]
        assert len(records) == 1
        # Privacy: the structured INFO line must not carry raw user input.
        assert not hasattr(records[0], "input_text")
        assert not hasattr(records[0], "user_input")

    @patch("wit.services.cache")
    def test_generate_returns_cached(self, mock_cache, persona_no):
        mock_cache.get.side_effect = lambda key: (
            persona_no if key.startswith("persona:") else "Cached response"
        )

        result = WitService.generate("say-no")

        assert result["cached"] is True
        assert result["response"] == "Cached response"

    def test_generate_unknown_persona_raises(self):
        with pytest.raises(PersonaNotFoundError):
            WitService.generate("nonexistent")
