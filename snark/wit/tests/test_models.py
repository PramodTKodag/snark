import pytest
from wit.models import Persona, ResponseLog


@pytest.mark.django_db
class TestPersona:
    def test_create_persona(self, persona_no):
        assert persona_no.slug == "say-no"
        assert persona_no.name == "The Refusal Artist"
        assert persona_no.is_active is True

    def test_slug_unique(self, persona_no):
        with pytest.raises(Exception):
            Persona.objects.create(
                slug="say-no",
                name="Duplicate",
                system_prompt="dup",
                tone="test",
            )


@pytest.mark.django_db
class TestResponseLog:
    def test_create_response_log(self, persona_no):
        log = ResponseLog.objects.create(
            persona=persona_no,
            input_text="test",
            response_text="response",
            tokens_used=10,
            latency_ms=100,
            provider_name="claude",
            model_name="claude-haiku-4-20250414",
        )
        assert log.persona == persona_no
        assert log.response_text == "response"
