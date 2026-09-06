import pytest

URL = "/v1/wit/metrics/"


@pytest.mark.django_db
def test_metrics_404_when_token_unset(client, settings):
    settings.METRICS_AUTH_TOKEN = ""
    assert client.get(URL).status_code == 404


@pytest.mark.django_db
def test_metrics_404_without_authorization(client, settings):
    settings.METRICS_AUTH_TOKEN = "secret-token"
    assert client.get(URL).status_code == 404


@pytest.mark.django_db
def test_metrics_404_with_wrong_token(client, settings):
    settings.METRICS_AUTH_TOKEN = "secret-token"
    resp = client.get(URL, HTTP_AUTHORIZATION="Bearer wrong")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_metrics_200_with_correct_token(client, settings):
    settings.METRICS_AUTH_TOKEN = "secret-token"
    resp = client.get(URL, HTTP_AUTHORIZATION="Bearer secret-token")
    assert resp.status_code == 200
    assert "text/plain" in resp["Content-Type"]
