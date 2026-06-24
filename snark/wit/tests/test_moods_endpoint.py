import pytest
from rest_framework.test import APIClient
from wit.constants import ALLOWED_LENGTHS, ALLOWED_MOODS


@pytest.mark.django_db
class TestMoodsEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

    def test_lists_all_moods_and_lengths(self):
        resp = self.client.get("/v1/wit/moods/")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["moods"]) == set(ALLOWED_MOODS)
        assert set(data["lengths"]) == set(ALLOWED_LENGTHS)

    def test_moods_are_sorted(self):
        moods = self.client.get("/v1/wit/moods/").json()["moods"]
        assert moods == sorted(moods)

    def test_lengths_are_in_logical_order(self):
        lengths = self.client.get("/v1/wit/moods/").json()["lengths"]
        assert lengths == ["short", "medium", "long"]
