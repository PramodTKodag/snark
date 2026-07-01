from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

MIN_PASSWORD_LENGTH = 12


class Command(BaseCommand):
    help = (
        "Create or update the admin superuser from ADMIN_USERNAME / ADMIN_EMAIL "
        "/ ADMIN_PASSWORD settings. Idempotent; a no-op when they are unset."
    )

    def handle(self, *args, **options):
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD
        email = settings.ADMIN_EMAIL

        if not username or not password:
            self.stdout.write(
                "ADMIN_USERNAME/ADMIN_PASSWORD not set — skipping admin bootstrap."
            )
            return

        if len(password) < MIN_PASSWORD_LENGTH:
            raise CommandError(
                f"ADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters."
            )

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if email:
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} superuser '{username}'."))
