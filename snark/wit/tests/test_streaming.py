from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from wit.models import ResponseLog
from wit.providers.base import AIProvider, AIResponse
from wit.services import WitService


class _OneShotProvider(AIProvider):
    """Provider with no streaming override — exercises the base fallback."""

    @property
    def name(self):
        return "dummy"

    def generate(self, system_prompt, user_prompt, temperature=0.9, max_tokens=200):
        return AIResponse(
            text="whole thing", tokens_used=1, model="m", provider="dummy"
        )

    def health_check(self):
        return True


def test_base_generate_stream_yields_whole_text():
    out = list(_OneShotProvider().generate_stream("sys", "user"))
    assert out == ["whole thing"]


@pytest.mark.django_db
class TestServiceStreaming:
    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_yields_deltas_then_done_and_logs(
        self, mock_cache, mock_registry, persona_no
    ):
        mock_cache.get.return_value = None
        provider = MagicMock()
        provider.name = "groq"
        provider._model = "test-model"
        provider.generate_stream.return_value = iter(["No", " thanks"])
        mock_registry.get.return_value = provider
        mock_registry.get_fallbacks.return_value = []

        events = list(WitService.generate_stream("say-no"))

        deltas = [e["delta"] for e in events if "delta" in e]
        assert "".join(deltas) == "No thanks"
        assert events[-1] == {"persona": "The Refusal Artist", "done": True}
        log = ResponseLog.objects.get(persona=persona_no)
        assert log.response_text == "No thanks"
        assert log.provider_name == "groq"
        assert log.model_name == "test-model"


@pytest.mark.django_db
class TestStreamingEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        self.client = APIClient()

    @patch("wit.views.WitService.generate_stream")
    def test_stream_true_returns_sse(self, mock_stream, persona_no):
        mock_stream.return_value = iter(
            [{"delta": "Hi"}, {"persona": "The Refusal Artist", "done": True}]
        )
        resp = self.client.get("/v1/wit/say-no/?stream=true")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/event-stream")
        body = b"".join(resp.streaming_content).decode()
        assert 'data: {"delta": "Hi"}' in body
        assert "data: [DONE]" in body

    @patch("wit.views.WitService.generate_stream")
    def test_accept_event_stream_header_is_negotiable(self, mock_stream, persona_no):
        # A real SSE client sends Accept: text/event-stream; it must not 406.
        mock_stream.return_value = iter(
            [{"persona": "The Refusal Artist", "done": True}]
        )
        resp = self.client.get(
            "/v1/wit/say-no/?stream=true", HTTP_ACCEPT="text/event-stream"
        )
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/event-stream")

    @patch("wit.views.WitService.generate")
    @patch("wit.views.WitService.generate_stream")
    def test_default_is_not_streamed(self, mock_stream, mock_gen, persona_no):
        mock_gen.return_value = {
            "response": "Nope",
            "persona": "The Refusal Artist",
            "cached": False,
        }
        resp = self.client.get("/v1/wit/say-no/")
        assert resp.status_code == 200
        assert resp.json()["response"] == "Nope"
        mock_stream.assert_not_called()
