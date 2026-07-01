from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from wit.maintenance import prune_response_logs
from wit.models import ResponseLog


def _log(persona, age_days):
    log = ResponseLog.objects.create(
        persona=persona,
        input_text="",
        response_text="hi",
        provider_name="groq",
        model_name="m",
    )
    # created_at is auto_now_add, so backdate it with an explicit update.
    old = timezone.now() - timedelta(days=age_days)
    ResponseLog.objects.filter(pk=log.pk).update(created_at=old)
    return log


@pytest.mark.django_db
def test_prune_deletes_only_old_rows(persona_no):
    _log(persona_no, age_days=100)
    _log(persona_no, age_days=10)
    deleted = prune_response_logs(30)
    assert deleted == 1
    assert ResponseLog.objects.count() == 1


@pytest.mark.django_db
def test_prune_rejects_negative_days(persona_no):
    with pytest.raises(ValueError):
        prune_response_logs(-1)


@pytest.mark.django_db
def test_prune_logs_command(persona_no):
    _log(persona_no, age_days=200)
    call_command("prune_logs", "--days", "90")
    assert ResponseLog.objects.count() == 0
