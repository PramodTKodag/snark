from rest_framework import serializers


class WitResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    persona = serializers.CharField()
    cached = serializers.BooleanField()


class WitInputSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, max_length=500, default="")


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    service = serializers.CharField()
    version = serializers.CharField()
    components = serializers.DictField()
