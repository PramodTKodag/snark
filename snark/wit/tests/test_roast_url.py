from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from wit.url_fetch import FetchedPage, UnsafeUrlError, UrlUnreachableError

_HTML = (
    '<html><head><meta property="og:title" content="Cool Launch">'
    '<meta property="og:site_name" content="ProductHunt"></head></html>'
)


@pytest.mark.django_db
class TestRoastUrlEndpoint:
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
        cache.clear()  # LocMemCache persists across tests; isolate the URL cache
        self.client = APIClient()

    @patch("wit.views.WitService.generate")
    @patch("wit.views.fetch_url")
    def test_success(self, mock_fetch, mock_gen, persona_roast):
        mock_fetch.return_value = FetchedPage(
            html=_HTML, final_url="https://example.com/x"
        )
        mock_gen.return_value = {
            "response": "Roasted",
            "persona": "The Friendly Roaster",
            "cached": False,
        }
        resp = self.client.get("/v1/wit/roast-url/?url=https://example.com/x")
        assert resp.status_code == 200
        assert mock_gen.call_args.kwargs["slug"] == "roast"
        user_input = mock_gen.call_args.kwargs["user_input"]
        assert "example.com" in user_input
        assert "Cool Launch" in user_input

    def test_missing_url_param(self, persona_roast):
        resp = self.client.get("/v1/wit/roast-url/")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    def test_invalid_url(self, persona_roast):
        resp = self.client.get("/v1/wit/roast-url/?url=not-a-url")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_request"

    @patch("wit.views.fetch_url")
    def test_unsafe_url(self, mock_fetch, persona_roast):
        mock_fetch.side_effect = UnsafeUrlError("blocked")
        resp = self.client.get("/v1/wit/roast-url/?url=http://169.254.169.254/")
        assert resp.status_code == 400
        assert resp.json()["code"] == "unsafe_url"

    @patch("wit.views.fetch_url")
    def test_url_unreachable(self, mock_fetch, persona_roast):
        mock_fetch.side_effect = UrlUnreachableError("timeout")
        resp = self.client.get("/v1/wit/roast-url/?url=https://example.com/")
        assert resp.status_code == 502
        assert resp.json()["code"] == "url_unreachable"

    @patch("wit.views.WitService.generate")
    @patch("wit.views.fetch_url")
    def test_cache_hit_skips_refetch(self, mock_fetch, mock_gen, persona_roast):
        mock_fetch.return_value = FetchedPage(
            html=_HTML, final_url="https://example.com/x"
        )
        mock_gen.return_value = {
            "response": "Roasted",
            "persona": "The Friendly Roaster",
            "cached": False,
        }
        url = "/v1/wit/roast-url/?url=https://example.com/x"
        self.client.get(url)
        self.client.get(url)
        assert mock_fetch.call_count == 1
