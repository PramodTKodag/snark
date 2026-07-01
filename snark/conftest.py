import importlib

import pytest
from rest_framework.test import APIClient
from wit.models import Persona


@pytest.fixture(scope="session", autouse=True)
def _rebuild_urlconf_admin_disabled():
    """Rebuild the URL conf with ADMIN_ENABLED=False at session start.

    The dev .env has ADMIN_ENABLED=True, so base.urls is imported at
    Django setup with the admin route already wired in. Reset it once
    per session to match the default (False) so routing tests that
    assert 404 for /admin/ pass without modifying the dev environment.
    """
    import base.urls as _urls
    from django.conf import settings as django_settings
    from django.urls import clear_url_caches

    original = django_settings.ADMIN_ENABLED
    django_settings.ADMIN_ENABLED = False
    importlib.reload(_urls)
    clear_url_caches()
    yield
    django_settings.ADMIN_ENABLED = original
    importlib.reload(_urls)
    clear_url_caches()


@pytest.fixture(autouse=True)
def _disable_ssl_redirect(settings):
    """Keep the test client on HTTP.

    Production runs with DEBUG=False, which enables SECURE_SSL_REDIRECT. CI
    also runs the suite with DEBUG=False, so without this every test-client
    request would be 301-redirected to HTTPS before reaching a view. Disable
    the redirect for tests so they exercise the views directly; production
    behaviour is unchanged.
    """
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def persona_no(db):
    return Persona.objects.create(
        slug="say-no",
        name="The Refusal Artist",
        system_prompt="You are a creative refusal generator.",
        rules=["Keep it short", "Be creative"],
        tone="witty",
        temperature=0.95,
        max_tokens=200,
        is_active=True,
    )


@pytest.fixture
def persona_roast(db):
    return Persona.objects.create(
        slug="roast",
        name="The Friendly Roaster",
        system_prompt="You roast people playfully.",
        rules=["Be playful", "Use name puns"],
        tone="playful",
        temperature=0.9,
        max_tokens=200,
        is_active=True,
    )
