import pytest

from wit.models import Persona, ProviderConfig, ResponseLog


@pytest.mark.django_db
class TestPersona:
    def test_create_persona(self, persona_no):
        assert persona_no.slug == "no"
        assert persona_no.name == "The Refusal Artist"
        assert persona_no.is_active is True

    def test_slug_unique(self, persona_no):
        with pytest.raises(Exception):
            Persona.objects.create(
                slug="no",
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


@pytest.mark.django_db
class TestProviderConfig:
    def test_create_provider_config(self):
        config = ProviderConfig.objects.create(
            provider_name="claude",
            model_name="claude-haiku-4-20250414",
            api_key_env_var="ANTHROPIC_API_KEY",
            is_default=True,
        )
        assert config.provider_name == "claude"
        assert config.is_default is True

    def test_provider_name_unique(self):
        ProviderConfig.objects.create(
            provider_name="claude",
            model_name="model-a",
            api_key_env_var="KEY_A",
        )
        with pytest.raises(Exception):
            ProviderConfig.objects.create(
                provider_name="claude",
                model_name="model-b",
                api_key_env_var="KEY_B",
            )
