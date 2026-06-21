import pytest
from django.core.management import call_command
from wit.management.commands.seed_personas import PERSONAS
from wit.models import Persona


@pytest.mark.django_db
class TestSeedPersonas:
    def test_seed_creates_all_personas(self):
        call_command("seed_personas")
        assert Persona.objects.count() == len(PERSONAS)

    def test_seed_is_idempotent(self):
        call_command("seed_personas")
        call_command("seed_personas")
        assert Persona.objects.count() == len(PERSONAS)

    def test_seed_slugs_match_definitions(self):
        call_command("seed_personas")
        expected = {p["slug"] for p in PERSONAS}
        actual = set(Persona.objects.values_list("slug", flat=True))
        assert actual == expected

    def test_seed_slugs_are_unique(self):
        slugs = [p["slug"] for p in PERSONAS]
        assert len(slugs) == len(set(slugs))
