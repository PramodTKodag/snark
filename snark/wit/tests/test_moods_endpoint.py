import pytest
from rest_framework.test import APIClient
from wit.constants import ALLOWED_MOODS


@pytest.mark.django_db
class TestMoodsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

    def test_lists_all_moods(self):
        resp = self.client.get("/v1/wit/moods/")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["moods"]) == set(ALLOWED_MOODS)

    def test_moods_are_sorted(self):
        moods = self.client.get("/v1/wit/moods/").json()["moods"]
        assert moods == sorted(moods)

    def test_response_has_no_lengths_key(self):
        # /moods/ is moods-only; lengths live as a fixed enum on each endpoint.
        assert "lengths" not in self.client.get("/v1/wit/moods/").json()
