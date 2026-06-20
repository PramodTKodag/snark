from rest_framework import serializers

from .constants import ALLOWED_MOODS


class WitResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    persona = serializers.CharField()
    cached = serializers.BooleanField()


class WitQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")
    mood = serializers.ChoiceField(
        choices=sorted(ALLOWED_MOODS), required=False, allow_blank=True
    )


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    service = serializers.CharField()
    version = serializers.CharField()
    components = serializers.DictField()
