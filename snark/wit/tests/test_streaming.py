from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from wit.models import ResponseLog
from wit.providers.base import AIProvider, AIResponse, StreamUsage
from wit.providers.claude_provider import ClaudeProvider
from wit.providers.gemini_provider import GeminiProvider
from wit.providers.groq_provider import GroqProvider
from wit.services import WitService


class _OneShotProvider(AIProvider):
    """Provider with no streaming override — exercises the base fallback."""

    @property
    def name(self):
        return "dummy"

    def generate(self, system_prompt, user_prompt, temperature=0.9, max_tokens=200):
        return AIResponse(
            text="whole thing",
            tokens_used=7,
            model="m",
            provider="dummy",
            input_tokens=3,
            output_tokens=4,
        )

    def health_check(self):
        return True


def test_base_generate_stream_yields_text_then_usage():
    out = list(_OneShotProvider().generate_stream("sys", "user"))
    assert out[0] == "whole thing"
    assert out[-1] == StreamUsage(input_tokens=3, output_tokens=4)
    assert out[-1].tokens_used == 7


class TestProviderStreamUsage:
    @patch("groq.Groq")
    def test_groq_stream_yields_deltas_then_usage(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        c1 = MagicMock(
            usage=None,
            choices=[MagicMock(finish_reason=None, delta=MagicMock(content="No"))],
        )
        c2 = MagicMock(
            usage=None,
            choices=[MagicMock(finish_reason=None, delta=MagicMock(content=" thanks"))],
        )
        # Final chunk (include_usage): empty choices, populated usage.
        usage_chunk = MagicMock(
            choices=[], usage=MagicMock(prompt_tokens=11, completion_tokens=4)
        )
        client.chat.completions.create.return_value = iter([c1, c2, usage_chunk])

        out = list(GroqProvider(api_key="k", model="m").generate_stream("s", "u"))

        assert [o for o in out if isinstance(o, str)] == ["No", " thanks"]
        assert out[-1] == StreamUsage(input_tokens=11, output_tokens=4)

    @patch("anthropic.Anthropic")
    def test_claude_stream_yields_deltas_then_usage(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        stream_ctx = MagicMock()
        stream_ctx.text_stream = iter(["No", " thanks"])
        stream_ctx.get_final_message.return_value = MagicMock(
            usage=MagicMock(input_tokens=9, output_tokens=5)
        )
        client.messages.stream.return_value.__enter__.return_value = stream_ctx

        out = list(ClaudeProvider(api_key="k", model="m").generate_stream("s", "u"))

        assert [o for o in out if isinstance(o, str)] == ["No", " thanks"]
        assert out[-1] == StreamUsage(input_tokens=9, output_tokens=5)

    @patch("google.genai.Client")
    def test_gemini_stream_yields_deltas_then_usage(self, mock_cls):
        client = MagicMock()
        mock_cls.return_value = client
        c1 = MagicMock(
            prompt_feedback=None, candidates=[], text="No", usage_metadata=None
        )
        c2 = MagicMock(
            prompt_feedback=None,
            candidates=[],
            text=" thanks",
            usage_metadata=MagicMock(prompt_token_count=20, candidates_token_count=6),
        )
        client.models.generate_content_stream.return_value = iter([c1, c2])

        out = list(GeminiProvider(api_key="k", model="m").generate_stream("s", "u"))

        assert [o for o in out if isinstance(o, str)] == ["No", " thanks"]
        assert out[-1] == StreamUsage(input_tokens=20, output_tokens=6)


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

    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_stream_persists_split_tokens(self, mock_cache, mock_registry, persona_no):
        mock_cache.get.return_value = None
        provider = MagicMock()
        provider.name = "claude"
        provider._model = "test-model"
        provider.generate_stream.return_value = iter(
            ["No", " thanks", StreamUsage(input_tokens=9, output_tokens=5)]
        )
        mock_registry.get.return_value = provider
        mock_registry.get_fallbacks.return_value = []

        events = list(WitService.generate_stream("say-no"))

        deltas = [e["delta"] for e in events if "delta" in e]
        # The usage marker must not leak into the SSE deltas.
        assert deltas == ["No", " thanks"]
        assert "".join(deltas) == "No thanks"
        log = ResponseLog.objects.get(persona=persona_no)
        assert log.input_tokens == 9
        assert log.output_tokens == 5
        assert log.tokens_used == 14


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
