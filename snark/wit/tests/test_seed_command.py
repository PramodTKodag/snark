import pytest
from django.core.management import call_command

from wit.models import Persona


@pytest.mark.django_db
class TestSeedPersonas:
    def test_seed_creates_10_personas(self):
        call_command("seed_personas")
        assert Persona.objects.count() == 10

    def test_seed_is_idempotent(self):
        call_command("seed_personas")
        call_command("seed_personas")
        assert Persona.objects.count() == 10

    def test_seed_creates_expected_slugs(self):
        call_command("seed_personas")
        expected = {
            "no", "excuse", "roast", "corporate", "commit",
            "hot-take", "compliment", "worth-it", "eli5", "blame",
        }
        actual = set(Persona.objects.values_list("slug", flat=True))
        assert actual == expected
