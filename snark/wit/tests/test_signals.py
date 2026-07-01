import pytest
from django.core.cache import cache
from wit.models import Persona
from wit.services import persona_cache_key


@pytest.mark.django_db
class TestPersonaCacheInvalidation:
    def test_save_clears_cache(self, persona_no):
        key = persona_cache_key(persona_no.slug)
        cache.set(key, persona_no, 3600)
        persona_no.name = "Renamed"
        persona_no.save()
        assert cache.get(key) is None

    def test_delete_clears_cache(self, persona_no):
        key = persona_cache_key(persona_no.slug)
        cache.set(key, persona_no, 3600)
        persona_no.delete()
        assert cache.get(key) is None


@pytest.mark.django_db
def test_persona_save_invalidates_personas_list_cache():
    cache.set("wit:personas:list", ["stale"], 300)
    persona = Persona.objects.create(
        slug="temp-x", name="X", system_prompt="x", rules=[], tone="x"
    )
    assert cache.get("wit:personas:list") is None  # post_save cleared it
    cache.set("wit:personas:list", ["stale2"], 300)
    persona.delete()
    assert cache.get("wit:personas:list") is None  # post_delete cleared it
