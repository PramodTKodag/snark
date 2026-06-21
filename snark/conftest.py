import pytest
from rest_framework.test import APIClient
from wit.models import Persona


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
