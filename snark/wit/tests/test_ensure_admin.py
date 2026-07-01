import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

User = get_user_model()


@pytest.mark.django_db
def test_noop_when_env_unset(settings):
    settings.ADMIN_USERNAME = ""
    settings.ADMIN_PASSWORD = ""
    call_command("ensure_admin")
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_creates_superuser_from_env(settings):
    settings.ADMIN_USERNAME = "root"
    settings.ADMIN_EMAIL = "root@example.com"
    settings.ADMIN_PASSWORD = "supersecret123"
    call_command("ensure_admin")
    user = User.objects.get(username="root")
    assert user.is_superuser and user.is_staff
    assert user.email == "root@example.com"
    assert user.check_password("supersecret123")


@pytest.mark.django_db
def test_is_idempotent_and_updates_password(settings):
    settings.ADMIN_USERNAME = "root"
    settings.ADMIN_EMAIL = "root@example.com"
    settings.ADMIN_PASSWORD = "supersecret123"
    call_command("ensure_admin")
    settings.ADMIN_PASSWORD = "rotatedsecret456"
    call_command("ensure_admin")
    assert User.objects.filter(username="root").count() == 1
    assert User.objects.get(username="root").check_password("rotatedsecret456")


@pytest.mark.django_db
def test_rejects_weak_password(settings):
    settings.ADMIN_USERNAME = "root"
    settings.ADMIN_PASSWORD = "short"
    with pytest.raises(CommandError):
        call_command("ensure_admin")
