import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from wit.models import Persona


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def persona_no(db):
    return Persona.objects.create(
        slug="no",
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
