from django.contrib import admin

from .models import Persona, ProviderConfig, ResponseLog


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tone", "temperature", "is_active", "updated_at")
    list_filter = ("is_active", "tone")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display = ("persona", "ip_address", "tokens_used", "latency_ms", "provider_name", "created_at")
    list_filter = ("provider_name", "persona")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"


@admin.register(ProviderConfig)
class ProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "model_name", "is_default", "is_active", "updated_at")
    list_filter = ("is_active", "is_default")
    readonly_fields = ("id", "created_at", "updated_at")
