import pytest
from django.core.cache import cache
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
