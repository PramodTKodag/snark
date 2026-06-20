from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestWitViews:
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
    def test_no_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Nope", "persona": "The Refusal Artist", "cached": False}
        resp = self.client.get("/v1/wit/say-no/")
        assert resp.status_code == 200
        assert resp.json()["response"] == "Nope"

    @patch("wit.views.WitService.generate")
    def test_excuse_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Busy", "persona": "The Excuse Machine", "cached": False}
        resp = self.client.get("/v1/wit/random-excuse/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_corporate_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Synergy", "persona": "The Synergy Maximizer", "cached": False}
        resp = self.client.get("/v1/wit/corporate-jargon/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_commit_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "fix: stuff", "persona": "The Honest Committer", "cached": False}
        resp = self.client.get("/v1/wit/commit-message/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_hot_take_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Hot take", "persona": "The Hot Take Machine", "cached": False}
        resp = self.client.get("/v1/wit/hot-take/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_compliment_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Great job", "persona": "The Wholesome Bot", "cached": False}
        resp = self.client.get("/v1/wit/compliment/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_blame_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "It was npm", "persona": "The Blame Allocator", "cached": False}
        resp = self.client.get("/v1/wit/bug-blame/")
        assert resp.status_code == 200

    @patch("wit.views.WitService.generate")
    def test_roast_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Roasted", "persona": "The Friendly Roaster", "cached": False}
        resp = self.client.get("/v1/wit/roast/Pramod/")
        assert resp.status_code == 200

    def test_roast_empty_name(self):
        resp = self.client.get("/v1/wit/roast/!!!/")
        assert resp.status_code == 400

    @patch("wit.views.WitService.generate")
    def test_worth_it_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "VERDICT: YES", "persona": "The Decision Oracle", "cached": False}
        resp = self.client.get("/v1/wit/worth-it/", {"q": "learning Rust"})
        assert resp.status_code == 200

    def test_worth_it_missing_q(self):
        resp = self.client.get("/v1/wit/worth-it/")
        assert resp.status_code == 400

    @patch("wit.views.WitService.generate")
    def test_eli5_endpoint(self, mock_gen):
        mock_gen.return_value = {"response": "Like cookies", "persona": "The Kindergarten Professor", "cached": False}
        resp = self.client.get("/v1/wit/explain-like-im-5/", {"q": "kubernetes"})
        assert resp.status_code == 200

    def test_eli5_missing_q(self):
        resp = self.client.get("/v1/wit/explain-like-im-5/")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestHealthViews:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        self.client = APIClient()

    def test_liveness(self):
        resp = self.client.get("/v1/wit/health/live/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readiness(self):
        resp = self.client.get("/v1/wit/health/ready/")
        assert resp.status_code == 200

    def test_health_status(self):
        resp = self.client.get("/v1/wit/health/status/")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "components" in data
        assert "database" in data["components"]
