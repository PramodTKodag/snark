import re

from rest_framework import serializers

from .constants import ALLOWED_LENGTHS, ALLOWED_MOODS, MAX_BATCH_SIZE, MAX_LANG_LENGTH


def clean_lang(value: str) -> str:
    """Sanitize a free-text language value before it reaches the prompt.

    Keeps letters, spaces and hyphens only (covers "Brazilian Portuguese",
    "Pirate-English") and bounds the length.
    """
    return re.sub(r"[^A-Za-z \-]", "", value)[:MAX_LANG_LENGTH].strip()


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
        return clean_lang(value)


class BatchItemSerializer(serializers.Serializer):
    persona = serializers.CharField(max_length=60)
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

    def validate_lang(self, value):
        return clean_lang(value)


class ReplyRequestSerializer(serializers.Serializer):
    post = serializers.CharField(max_length=2000)
    mood = serializers.ChoiceField(
        choices=sorted(ALLOWED_MOODS), required=False, allow_blank=True
    )
    length = serializers.ChoiceField(
        choices=sorted(ALLOWED_LENGTHS), required=False, allow_blank=True
    )
    lang = serializers.CharField(
        required=False, allow_blank=True, max_length=MAX_LANG_LENGTH, default=""
    )

    def validate_post(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Post text must not be empty.")
        return cleaned

    def validate_lang(self, value):
        return clean_lang(value)


class BatchRequestSerializer(serializers.Serializer):
    requests = BatchItemSerializer(many=True, allow_empty=False)

    def validate_requests(self, value):
        if len(value) > MAX_BATCH_SIZE:
            raise serializers.ValidationError(
                f"A batch may contain at most {MAX_BATCH_SIZE} requests."
            )
        return value


class BatchResponseSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.DictField())


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
