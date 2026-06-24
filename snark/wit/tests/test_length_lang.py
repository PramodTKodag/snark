from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from wit.constants import LENGTH_MAX_TOKENS
from wit.providers.base import AIResponse
from wit.serializers import WitQuerySerializer
from wit.services import WitService


class TestWitQuerySerializer:
    def test_valid_length(self):
        s = WitQuerySerializer(data={"length": "short"})
        assert s.is_valid()
        assert s.validated_data["length"] == "short"

    def test_invalid_length_rejected(self):
        s = WitQuerySerializer(data={"length": "gigantic"})
        assert not s.is_valid()
        assert "length" in s.errors

    def test_lang_is_sanitized(self):
        s = WitQuerySerializer(data={"lang": "Spanish; DROP TABLE"})
        assert s.is_valid()
        assert s.validated_data["lang"] == "Spanish DROP TABLE"


class TestPromptAndCacheKey:
    def test_length_and_lang_in_prompt(self, persona_no):
        prompt = WitService._build_prompt(
            persona_no, mood=None, length="long", lang="French"
        )
        assert "LENGTH:" in prompt
        assert "LANGUAGE: Write your entire response in French" in prompt

    def test_cache_key_varies_by_length_and_lang(self):
        base = WitService._response_cache_key("roast", "Dave", None, None, None)
        by_len = WitService._response_cache_key("roast", "Dave", None, "short", None)
        by_lang = WitService._response_cache_key("roast", "Dave", None, None, "French")
        assert len({base, by_len, by_lang}) == 3


@pytest.mark.django_db
class TestLengthOverridesMaxTokens:
    @patch("wit.services.ProviderRegistry")
    @patch("wit.services.cache")
    def test_length_sets_max_tokens(self, mock_cache, mock_registry, persona_no):
        mock_cache.get.return_value = None
        provider = MagicMock()
        provider.generate.return_value = AIResponse(
            text="ok", tokens_used=1, model="m", provider="groq", latency_ms=1
        )
        mock_registry.get.return_value = provider

        WitService.generate("say-no", length="short")

        assert provider.generate.call_args.kwargs["max_tokens"] == (
            LENGTH_MAX_TOKENS["short"]
        )


@pytest.mark.django_db
class TestViewPassesLengthLang:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        settings.REST_FRAMEWORK = {
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
            "DEFAULT_AUTHENTICATION_CLASSES": [],
            "DEFAULT_PERMISSION_CLASSES": [],
            "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        }
        self.client = APIClient()

    @patch("wit.views.WitService.generate")
    def test_passthrough(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        self.client.get("/v1/wit/say-no/", {"length": "short", "lang": "Spanish"})
        kwargs = mock_gen.call_args.kwargs
        assert kwargs["length"] == "short"
        assert kwargs["lang"] == "Spanish"
