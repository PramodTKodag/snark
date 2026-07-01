from base.admin import snark_admin_site
from django.contrib import admin
from django.core.cache import cache

from .maintenance import prune_response_logs
from .models import Persona, ResponseLog
from .services import persona_cache_key


@admin.register(Persona, site=snark_admin_site)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tone", "temperature", "is_active", "updated_at")
    list_editable = ("is_active",)
    list_filter = ("is_active", "tone")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    actions = ("activate", "deactivate", "duplicate_persona", "clear_persona_cache")

    def _invalidate(self, slugs):
        """Bulk queryset updates bypass model signals, so clear caches by hand."""
        for slug in slugs:
            cache.delete(persona_cache_key(slug))
        cache.delete("wit:personas:list")

    @admin.action(description="Activate selected personas")
    def activate(self, request, queryset):
        slugs = list(queryset.values_list("slug", flat=True))
        count = queryset.update(is_active=True)
        self._invalidate(slugs)
        self.message_user(request, f"Activated {count} persona(s).")

    @admin.action(description="Deactivate selected personas")
    def deactivate(self, request, queryset):
        slugs = list(queryset.values_list("slug", flat=True))
        count = queryset.update(is_active=False)
        self._invalidate(slugs)
        self.message_user(request, f"Deactivated {count} persona(s).")

    @admin.action(description="Duplicate selected personas (as inactive)")
    def duplicate_persona(self, request, queryset):
        count = 0
        for persona in queryset:
            base_slug = f"{persona.slug}-copy"
            slug = base_slug
            suffix = 2
            while Persona.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            Persona.objects.create(
                slug=slug,
                name=f"{persona.name} (copy)",
                system_prompt=persona.system_prompt,
                rules=persona.rules,
                tone=persona.tone,
                temperature=persona.temperature,
                max_tokens=persona.max_tokens,
                is_active=False,
            )
            count += 1
        self.message_user(request, f"Duplicated {count} persona(s) (created inactive).")

    @admin.action(description="Clear persona cache")
    def clear_persona_cache(self, request, queryset):
        slugs = list(queryset.values_list("slug", flat=True))
        self._invalidate(slugs)
        self.message_user(request, f"Cleared cache for {len(slugs)} persona(s).")


@admin.register(ResponseLog, site=snark_admin_site)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display = (
        "persona",
        "provider_name",
        "model_name",
        "tokens_used",
        "latency_ms",
        "created_at",
    )
    list_filter = ("provider_name", "persona", "created_at")
    search_fields = ("input_text", "response_text")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "persona",
        "input_text",
        "response_text",
        "tokens_used",
        "latency_ms",
        "provider_name",
        "model_name",
        "created_at",
    )
    actions = ("prune_30", "prune_90")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Delete ALL logs older than 30 days")
    def prune_30(self, request, queryset):
        count = prune_response_logs(30)
        self.message_user(request, f"Pruned {count} log(s) older than 30 days.")

    @admin.action(description="Delete ALL logs older than 90 days")
    def prune_90(self, request, queryset):
        count = prune_response_logs(90)
        self.message_user(request, f"Pruned {count} log(s) older than 90 days.")
