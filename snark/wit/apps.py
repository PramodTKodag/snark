from django.apps import AppConfig


class WitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wit"
    verbose_name = "Wit"

    def ready(self):
        from . import signals  # noqa: F401  (registers signal receivers)
