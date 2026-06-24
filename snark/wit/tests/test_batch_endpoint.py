from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from wit.services import PersonaNotFoundError


@pytest.mark.django_db
class TestBatchEndpoint:
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
    def test_multiple_personas_in_order(self, mock_gen):
        mock_gen.side_effect = [
            {"response": "Roasted", "persona": "The Friendly Roaster", "cached": False},
            {"response": "fix: it", "persona": "The Honest Committer", "cached": False},
        ]
        resp = self.client.post(
            "/v1/wit/batch/",
            {
                "requests": [
                    {"persona": "roast", "q": "Dave"},
                    {"persona": "commit-message"},
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert [r["persona"] for r in results] == [
            "The Friendly Roaster",
            "The Honest Committer",
        ]

    @patch("wit.views.WitService.generate")
    def test_passes_per_item_params(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        self.client.post(
            "/v1/wit/batch/",
            {
                "requests": [
                    {
                        "persona": "hot-take",
                        "q": "pizza",
                        "mood": "spicy",
                        "length": "short",
                        "lang": "Spanish",
                    }
                ]
            },
            format="json",
        )
        kwargs = mock_gen.call_args.kwargs
        assert kwargs == {
            "slug": "hot-take",
            "user_input": "pizza",
            "mood": "spicy",
            "length": "short",
            "lang": "Spanish",
        }

    @patch("wit.views.WitService.generate")
    def test_bad_persona_is_per_item_error(self, mock_gen):
        def side_effect(slug, **kwargs):
            if slug == "nope":
                raise PersonaNotFoundError(slug)
            return {
                "response": "ok",
                "persona": "The Hot Take Machine",
                "cached": False,
            }

        mock_gen.side_effect = side_effect
        resp = self.client.post(
            "/v1/wit/batch/",
            {"requests": [{"persona": "nope"}, {"persona": "hot-take"}]},
            format="json",
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["code"] == "persona_not_found"
        assert results[0]["persona"] == "nope"
        assert results[1]["response"] == "ok"

    def test_empty_requests_rejected(self):
        resp = self.client.post("/v1/wit/batch/", {"requests": []}, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    def test_too_many_requests_rejected(self):
        resp = self.client.post(
            "/v1/wit/batch/",
            {"requests": [{"persona": "hot-take"} for _ in range(6)]},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    def test_missing_persona_field_rejected(self):
        resp = self.client.post(
            "/v1/wit/batch/", {"requests": [{"q": "no persona"}]}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    def test_get_not_allowed(self):
        resp = self.client.get("/v1/wit/batch/")
        assert resp.status_code == 405
