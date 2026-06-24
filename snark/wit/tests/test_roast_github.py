from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from wit.github import GitHubError, GitHubUserNotFoundError, build_roast_context


@pytest.mark.django_db
class TestRoastGithubEndpoint:
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
    @patch("wit.views.fetch_profile")
    def test_success(self, mock_fetch, mock_gen, persona_roast):
        mock_fetch.return_value = {
            "login": "octocat",
            "public_repos": 8,
            "followers": 9000,
            "following": 9,
        }
        mock_gen.return_value = {
            "response": "Roasted",
            "persona": "The Friendly Roaster",
            "cached": False,
        }
        resp = self.client.get("/v1/wit/roast-github/octocat/")
        assert resp.status_code == 200
        # The GitHub context is fed to the roast persona as user_input.
        assert mock_gen.call_args.kwargs["slug"] == "roast"
        assert "octocat" in mock_gen.call_args.kwargs["user_input"]

    @patch("wit.views.fetch_profile")
    def test_user_not_found(self, mock_fetch, persona_roast):
        mock_fetch.side_effect = GitHubUserNotFoundError("ghost")
        resp = self.client.get("/v1/wit/roast-github/ghost/")
        assert resp.status_code == 404
        assert resp.json()["code"] == "github_user_not_found"

    @patch("wit.views.fetch_profile")
    def test_github_unavailable(self, mock_fetch, persona_roast):
        mock_fetch.side_effect = GitHubError("boom")
        resp = self.client.get("/v1/wit/roast-github/octocat/")
        assert resp.status_code == 503
        assert resp.json()["code"] == "github_unavailable"

    def test_invalid_username(self, persona_roast):
        resp = self.client.get("/v1/wit/roast-github/!!!/")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"


def test_build_roast_context_includes_stats():
    ctx = build_roast_context(
        {
            "login": "torvalds",
            "name": "Linus",
            "bio": "I make kernels",
            "public_repos": 7,
            "followers": 180000,
            "following": 0,
        }
    )
    assert "@torvalds" in ctx
    assert "Linus" in ctx
    assert "followers: 180000" in ctx
