from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestRandomEndpoint:
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
    def test_picks_a_persona(self, mock_gen, persona_roast):
        mock_gen.return_value = {
            "response": "Roasted",
            "persona": "The Friendly Roaster",
            "cached": False,
        }
        resp = self.client.get("/v1/wit/random/")
        assert resp.status_code == 200
        assert resp.json()["persona"] == "The Friendly Roaster"
        # Whatever slug was chosen, it must be the seeded one.
        assert mock_gen.call_args.kwargs["slug"] == "roast"

    @patch("wit.views.WitService.generate")
    def test_passes_through_params(self, mock_gen, persona_roast):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        self.client.get("/v1/wit/random/", {"q": "mondays", "mood": "unhinged"})
        kwargs = mock_gen.call_args.kwargs
        assert kwargs["user_input"] == "mondays"
        assert kwargs["mood"] == "unhinged"

    def test_404_when_no_personas(self):
        resp = self.client.get("/v1/wit/random/")
        assert resp.status_code == 404
        assert resp.json()["code"] == "persona_not_found"
