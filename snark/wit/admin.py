from base.admin import snark_admin_site
from django.contrib import admin
from django.core.cache import cache

from .models import (  # noqa: F401  (ResponseLog admin added in Task 4)
    Persona,
    ResponseLog,
)
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
