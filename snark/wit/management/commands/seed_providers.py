from django.core.management.base import BaseCommand

from wit.models import ProviderConfig


class Command(BaseCommand):
    help = "Seed default AI provider config (idempotent)"

    def handle(self, *args, **options):
        _, created = ProviderConfig.objects.update_or_create(
            provider_name="claude",
            defaults={
                "model_name": "claude-haiku-4-20250414",
                "api_key_env_var": "ANTHROPIC_API_KEY",
                "is_default": True,
                "is_active": True,
                "settings": {},
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Claude provider config"))
