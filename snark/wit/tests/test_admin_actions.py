import pytest
from base.admin import snark_admin_site
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.cache import cache
from django.test import RequestFactory
from wit.models import Persona
from wit.services import persona_cache_key


def _request():
    req = RequestFactory().post("/")
    # message_user needs a message store; CookieStorage needs no session.
    setattr(req, "_messages", CookieStorage(req))
    return req


@pytest.mark.django_db
def test_duplicate_persona_creates_inactive_copy(persona_no):
    from wit.admin import PersonaAdmin

    admin = PersonaAdmin(Persona, snark_admin_site)
    admin.duplicate_persona(_request(), Persona.objects.filter(pk=persona_no.pk))

    copy = Persona.objects.get(slug="say-no-copy")
    assert copy.is_active is False
    assert copy.system_prompt == persona_no.system_prompt
    assert copy.rules == persona_no.rules


@pytest.mark.django_db
def test_duplicate_persona_avoids_slug_collision(persona_no):
    from wit.admin import PersonaAdmin

    Persona.objects.create(
        slug="say-no-copy", name="x", system_prompt="x", rules=[], tone="x"
    )
    admin = PersonaAdmin(Persona, snark_admin_site)
    admin.duplicate_persona(_request(), Persona.objects.filter(pk=persona_no.pk))
    assert Persona.objects.filter(slug="say-no-copy-2").exists()


@pytest.mark.django_db
def test_deactivate_action_updates_and_clears_cache(persona_no):
    cache.set(persona_cache_key("say-no"), persona_no, 300)
    cache.set("wit:personas:list", ["stale"], 300)
    from wit.admin import PersonaAdmin

    admin = PersonaAdmin(Persona, snark_admin_site)
    admin.deactivate(_request(), Persona.objects.filter(pk=persona_no.pk))

    persona_no.refresh_from_db()
    assert persona_no.is_active is False
    assert cache.get(persona_cache_key("say-no")) is None
    assert cache.get("wit:personas:list") is None


@pytest.mark.django_db
def test_clear_persona_cache_action(persona_no):
    cache.set(persona_cache_key("say-no"), persona_no, 300)
    from wit.admin import PersonaAdmin

    admin = PersonaAdmin(Persona, snark_admin_site)
    admin.clear_persona_cache(_request(), Persona.objects.filter(pk=persona_no.pk))
    assert cache.get(persona_cache_key("say-no")) is None


@pytest.mark.django_db
def test_responselog_admin_is_view_only():
    from wit.admin import ResponseLogAdmin
    from wit.models import ResponseLog

    admin = ResponseLogAdmin(ResponseLog, snark_admin_site)
    assert admin.has_add_permission(_request()) is False
