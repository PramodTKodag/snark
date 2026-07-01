import pytest


def test_build_admin_patterns_disabled(settings):
    settings.ADMIN_ENABLED = False
    from base.urls import build_admin_patterns

    assert build_admin_patterns() == []


def test_build_admin_patterns_enabled(settings):
    settings.ADMIN_ENABLED = True
    settings.ADMIN_URL = "secret-admin/"
    from base.urls import build_admin_patterns

    patterns = build_admin_patterns()
    assert len(patterns) == 1


@pytest.mark.django_db
def test_admin_url_404_when_disabled(client):
    # ADMIN_ENABLED defaults to False, so the URLconf built at import has no
    # admin route and /admin/ must not resolve.
    resp = client.get("/admin/")
    assert resp.status_code == 404


def test_models_registered_on_snark_site():
    from base.admin import snark_admin_site
    from wit.models import Persona, ResponseLog

    assert Persona in snark_admin_site._registry
    assert ResponseLog in snark_admin_site._registry
