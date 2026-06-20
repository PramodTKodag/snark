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
        assert not hasattr(ResponseLog.objects.first(), "ip_address")

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
