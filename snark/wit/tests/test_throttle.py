from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestThrottle:
    @patch("wit.views.WitService.generate")
    def test_anonymous_requests_throttled_after_limit(self, mock_gen, settings):
        settings.CACHES = {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        }
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        cache.clear()
        client = APIClient()

        statuses = [client.get("/v1/wit/say-no/").status_code for _ in range(51)]

        assert statuses.count(200) == 50
        assert statuses[-1] == 429

        # Clear throttle counters so later tests are not affected.
        cache.clear()
