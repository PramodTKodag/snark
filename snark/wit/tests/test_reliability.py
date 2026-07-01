from unittest.mock import MagicMock, patch

import pytest
from wit import stats
from wit.models import GenerationEvent
from wit.providers.base import AIResponse, ContentFilterError, ProviderError
from wit.services import WitService


def _response(provider="groq", model="m"):
    return AIResponse(
        text="ok", tokens_used=1, model=model, provider=provider, latency_ms=1
    )


@pytest.mark.django_db
class TestGenerationEventRecording:
    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_primary_success_records_ok_event(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.return_value = _response("groq")
        mock_registry.get.return_value = primary

        WitService.generate("say-no")

        event = GenerationEvent.objects.get()
        assert event.success is True
        assert event.fell_back is False
        assert event.content_filtered is False
        assert event.streamed is False
        assert event.provider_name == "groq"
        assert event.persona_id == persona_no.id

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_fallback_success_records_fell_back(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = ProviderError("down")
        fallback = MagicMock()
        fallback.name = "gemini"
        fallback.generate.return_value = _response("gemini")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = [fallback]

        WitService.generate("say-no")

        event = GenerationEvent.objects.get()
        assert event.success is True
        assert event.fell_back is True
        assert event.content_filtered is False
        assert event.provider_name == "gemini"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_content_filter_softened_success_records_filtered(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = [
            ContentFilterError("blocked"),
            _response("groq"),
        ]
        mock_registry.get.return_value = primary

        WitService.generate("say-no")

        event = GenerationEvent.objects.get()
        assert event.success is True
        assert event.fell_back is False
        assert event.content_filtered is True

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_content_filter_then_fallback_records_filtered_and_fell_back(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        # primary filters, softened retry also filters -> fall back
        primary.generate.side_effect = [
            ContentFilterError("blocked"),
            ContentFilterError("still blocked"),
        ]
        fallback = MagicMock()
        fallback.name = "gemini"
        fallback.generate.return_value = _response("gemini")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = [fallback]

        WitService.generate("say-no")

        event = GenerationEvent.objects.get()
        assert event.success is True
        assert event.fell_back is True
        assert event.content_filtered is True

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_all_providers_fail_records_error_and_raises(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.side_effect = ProviderError("down")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = []

        with pytest.raises(ProviderError):
            WitService.generate("say-no")

        event = GenerationEvent.objects.get()
        assert event.success is False
        assert event.fell_back is False
        assert event.provider_name == "groq"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_recording_failure_does_not_break_generation(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate.return_value = _response("groq")
        mock_registry.get.return_value = primary

        with patch.object(
            GenerationEvent.objects, "create", side_effect=Exception("db down")
        ):
            result = WitService.generate("say-no")

        assert result["response"] == "ok"
        assert GenerationEvent.objects.count() == 0

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_stream_success_records_streamed_event(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        provider = MagicMock()
        provider.name = "groq"
        provider._model = "test-model"
        provider.generate_stream.return_value = iter(["No", " thanks"])
        mock_registry.get.return_value = provider
        mock_registry.get_fallbacks.return_value = []

        list(WitService.generate_stream("say-no"))

        event = GenerationEvent.objects.get()
        assert event.streamed is True
        assert event.success is True
        assert event.fell_back is False
        assert event.content_filtered is False
        assert event.provider_name == "groq"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_stream_fallback_records_fell_back(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate_stream.side_effect = ProviderError("down")
        fallback = MagicMock()
        fallback.name = "gemini"
        fallback._model = "test-model"
        fallback.generate_stream.return_value = iter(["No", " thanks"])
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = [fallback]

        list(WitService.generate_stream("say-no"))

        event = GenerationEvent.objects.get()
        assert event.streamed is True
        assert event.success is True
        assert event.fell_back is True
        assert event.provider_name == "gemini"

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_stream_all_fail_records_error_and_raises(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        primary = MagicMock()
        primary.name = "groq"
        primary.generate_stream.side_effect = ContentFilterError("blocked")
        mock_registry.get.return_value = primary
        mock_registry.get_fallbacks.return_value = []

        with pytest.raises(ProviderError):
            list(WitService.generate_stream("say-no"))

        event = GenerationEvent.objects.get()
        assert event.success is False
        assert event.streamed is True
        assert event.content_filtered is True


@pytest.mark.django_db
class TestReliabilityStats:
    def _event(self, **kwargs):
        defaults = dict(
            provider_name="groq",
            model_name="m",
            success=True,
            fell_back=False,
            content_filtered=False,
            streamed=False,
        )
        defaults.update(kwargs)
        return GenerationEvent.objects.create(**defaults)

    def test_reliability_stats_rates(self):
        for _ in range(2):
            self._event(success=False)
        for _ in range(3):
            self._event(fell_back=True)
        self._event(content_filtered=True)
        for _ in range(4):
            self._event()

        r = stats.reliability_stats()
        assert r["total"] == 10
        assert r["errors"] == 2
        assert r["fallbacks"] == 3
        assert r["filtered"] == 1
        assert r["error_rate"] == 20.0
        assert r["fallback_rate"] == 30.0
        assert r["content_filter_rate"] == 10.0

    def test_reliability_stats_empty(self):
        r = stats.reliability_stats()
        assert r["total"] == 0
        assert r["errors"] == 0
        assert r["error_rate"] == 0.0
        assert r["fallback_rate"] == 0.0
        assert r["content_filter_rate"] == 0.0

    def test_provider_error_breakdown(self):
        self._event(provider_name="groq", success=False)
        self._event(provider_name="groq", success=False)
        self._event(provider_name="gemini", success=False)
        self._event(provider_name="groq", success=True)  # not an error

        rows = stats.provider_error_breakdown()
        assert rows[0] == {"provider": "groq", "errors": 2}
        assert {"provider": "gemini", "errors": 1} in rows
