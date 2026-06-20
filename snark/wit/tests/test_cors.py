from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCors:
    @patch("wit.views.WitService.generate")
    def test_cors_header_present_for_cross_origin_request(self, mock_gen):
        mock_gen.return_value = {"response": "x", "persona": "p", "cached": False}
        client = APIClient()
        resp = client.get("/v1/wit/say-no/", HTTP_ORIGIN="https://example.com")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
