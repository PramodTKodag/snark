from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from wit.services import PersonaNotFoundError


@pytest.mark.django_db
class TestReplyEndpoint:
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
    def test_reply_to_post(self, mock_gen):
        mock_gen.return_value = {
            "response": "Bold prophecy.",
            "persona": "The Reply Guy",
            "cached": False,
        }
        resp = self.client.post(
            "/v1/wit/reply/",
            {"post": "Shipped with zero tests. What could go wrong?"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["persona"] == "The Reply Guy"
        kwargs = mock_gen.call_args.kwargs
        assert kwargs["slug"] == "reply"
        assert kwargs["user_input"] == "Shipped with zero tests. What could go wrong?"

    @patch("wit.views.WitService.generate")
    def test_defaults_to_short_length(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        self.client.post("/v1/wit/reply/", {"post": "hello world"}, format="json")
        assert mock_gen.call_args.kwargs["length"] == "short"

    @patch("wit.views.WitService.generate")
    def test_explicit_params_pass_through(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        self.client.post(
            "/v1/wit/reply/",
            {"post": "hello", "mood": "dramatic", "length": "long", "lang": "Spanish"},
            format="json",
        )
        kwargs = mock_gen.call_args.kwargs
        assert kwargs["mood"] == "dramatic"
        assert kwargs["length"] == "long"
        assert kwargs["lang"] == "Spanish"

    def test_missing_post_rejected(self):
        resp = self.client.post("/v1/wit/reply/", {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    def test_blank_post_rejected(self):
        resp = self.client.post("/v1/wit/reply/", {"post": "   "}, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    @patch("wit.views.WitService.generate")
    def test_missing_persona_returns_503(self, mock_gen):
        mock_gen.side_effect = PersonaNotFoundError("reply")
        resp = self.client.post("/v1/wit/reply/", {"post": "hi"}, format="json")
        assert resp.status_code == 503
        assert resp.json()["code"] == "persona_not_found"

    def test_get_not_allowed(self):
        resp = self.client.get("/v1/wit/reply/")
        assert resp.status_code == 405
