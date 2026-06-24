import re

from rest_framework import serializers

from .constants import ALLOWED_LENGTHS, ALLOWED_MOODS, MAX_LANG_LENGTH


class WitResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    persona = serializers.CharField()
    cached = serializers.BooleanField()


class WitQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False, allow_blank=True, max_length=500, default=""
    )
    mood = serializers.ChoiceField(
        choices=sorted(ALLOWED_MOODS), required=False, allow_blank=True
    )
    length = serializers.ChoiceField(
        choices=sorted(ALLOWED_LENGTHS), required=False, allow_blank=True
    )
    lang = serializers.CharField(
        required=False, allow_blank=True, max_length=MAX_LANG_LENGTH, default=""
    )
    stream = serializers.BooleanField(required=False, default=False)

    def validate_lang(self, value):
        # Free text lands in the prompt, so keep it to letters/spaces/hyphens
        # (covers "Brazilian Portuguese", "Pirate-English") and bound the length.
        return re.sub(r"[^A-Za-z \-]", "", value)[:MAX_LANG_LENGTH].strip()


class PersonaListItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    tone = serializers.CharField()


class PersonaStatSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class StatsResponseSerializer(serializers.Serializer):
    total_responses = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    personas = PersonaStatSerializer(many=True)


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    service = serializers.CharField()
    version = serializers.CharField()
    components = serializers.DictField()
