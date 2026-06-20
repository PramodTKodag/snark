from django.apps import AppConfig


class SnarkBaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base"
    verbose_name = "Snark Base"
