from django.contrib import admin

from .models import Persona, ResponseLog


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tone", "temperature", "is_active", "updated_at")
    list_filter = ("is_active", "tone")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display = (
        "persona",
        "tokens_used",
        "latency_ms",
        "provider_name",
        "created_at",
    )
    list_filter = ("provider_name", "persona")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"
