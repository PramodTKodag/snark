import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from wit.models import Persona, ResponseLog


@pytest.mark.django_db
class TestPersonaListEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        # LocMemCache is process-global; clear it so these list/stats responses
        # (which the views cache) don't leak between tests.
        cache.clear()
        self.client = APIClient()

    def test_lists_active_personas(self, persona_no, persona_roast):
        resp = self.client.get("/v1/wit/personas/")
        assert resp.status_code == 200
        slugs = {p["slug"] for p in resp.json()}
        assert {"say-no", "roast"} <= slugs
        first = resp.json()[0]
        assert set(first) == {"slug", "name", "tone"}

    def test_excludes_inactive(self, persona_no):
        Persona.objects.create(
            slug="hidden",
            name="Hidden",
            system_prompt="x",
            rules=[],
            tone="dry",
            is_active=False,
        )
        slugs = {p["slug"] for p in self.client.get("/v1/wit/personas/").json()}
        assert "hidden" not in slugs
        assert "say-no" in slugs

    def test_empty_when_no_personas(self):
        resp = self.client.get("/v1/wit/personas/")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.django_db
class TestStatsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        cache.clear()
        self.client = APIClient()

    def test_empty_stats(self):
        resp = self.client.get("/v1/wit/stats/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_responses"] == 0
        assert data["total_tokens"] == 0
        assert data["personas"] == []

    def test_aggregates_response_logs(self, persona_roast):
        for tokens in (10, 20, 30):
            ResponseLog.objects.create(
                persona=persona_roast,
                input_text="",
                response_text="roasted",
                tokens_used=tokens,
                latency_ms=5,
                provider_name="groq",
                model_name="test",
            )
        data = self.client.get("/v1/wit/stats/").json()
        assert data["total_responses"] == 3
        assert data["total_tokens"] == 60
        assert data["personas"][0]["slug"] == "roast"
        assert data["personas"][0]["count"] == 3
        # Stats expose only counts, never user input.
        assert "input_text" not in str(data)
