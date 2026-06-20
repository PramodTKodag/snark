import uuid

from django.db import models


class Persona(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True, db_index=True)
    name = models.CharField(max_length=100)
    system_prompt = models.TextField()
    rules = models.JSONField(default=list)
    tone = models.CharField(max_length=50)
    temperature = models.FloatField(default=0.9)
    max_tokens = models.IntegerField(default=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personas"

    def __str__(self):
        return f"{self.name} ({self.slug})"


class ResponseLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="response_logs"
    )
    input_text = models.TextField(blank=True, default="")
    response_text = models.TextField()
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    provider_name = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "response_logs"
        indexes = [
            models.Index(fields=["persona", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.persona.slug} @ {self.created_at}"
