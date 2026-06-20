import pytest

from wit.models import Persona
from wit.services import WitService


@pytest.mark.django_db
class TestBuildPrompt:
    def _persona(self, **overrides):
        defaults = dict(
            slug="t-persona",
            name="Tester",
            system_prompt="BASE PROMPT",
            rules=[],
            tone="deadpan",
            temperature=0.9,
            max_tokens=80,
            is_active=True,
        )
        defaults.update(overrides)
        return Persona.objects.create(**defaults)

    def test_tone_is_included(self):
        persona = self._persona(tone="deadpan")
        prompt = WitService._build_prompt(persona)
        assert "deadpan" in prompt

    def test_no_rules_header_when_empty(self):
        persona = self._persona(rules=[])
        prompt = WitService._build_prompt(persona)
        assert "Rules:" not in prompt

    def test_rules_header_present_when_rules_exist(self):
        persona = self._persona(rules=["Be brief"])
        prompt = WitService._build_prompt(persona)
        assert "Rules:" in prompt
        assert "- Be brief" in prompt

    def test_mood_override_included(self):
        persona = self._persona()
        prompt = WitService._build_prompt(persona, mood="sarcastic")
        assert "MOOD OVERRIDE" in prompt
        assert "sarcastic" in prompt
