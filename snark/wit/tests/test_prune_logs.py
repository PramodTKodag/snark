from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from wit.maintenance import prune_generation_events, prune_response_logs
from wit.models import GenerationEvent, ResponseLog


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


def _event(persona, age_days):
    event = GenerationEvent.objects.create(persona=persona, provider_name="groq")
    old = timezone.now() - timedelta(days=age_days)
    GenerationEvent.objects.filter(pk=event.pk).update(created_at=old)
    return event


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
def test_prune_events_deletes_only_old_rows(persona_no):
    _event(persona_no, age_days=200)
    _event(persona_no, age_days=10)
    deleted = prune_generation_events(90)
    assert deleted == 1
    assert GenerationEvent.objects.count() == 1


@pytest.mark.django_db
def test_prune_events_rejects_negative_days(persona_no):
    with pytest.raises(ValueError):
        prune_generation_events(-1)


@pytest.mark.django_db
def test_prune_logs_command_days_override_applies_to_both(persona_no):
    _log(persona_no, age_days=200)
    _event(persona_no, age_days=200)
    call_command("prune_logs", "--days", "90")
    assert ResponseLog.objects.count() == 0
    assert GenerationEvent.objects.count() == 0


@pytest.mark.django_db
def test_prune_logs_command_uses_retention_settings(persona_no, settings):
    settings.RESPONSE_LOG_RETENTION_DAYS = 30
    settings.GENERATION_EVENT_RETENTION_DAYS = 90
    # A 60-day-old log is past the 30-day log window but within the 90-day event
    # window, so only the log is pruned; the same-age event survives.
    _log(persona_no, age_days=60)
    _event(persona_no, age_days=60)
    call_command("prune_logs")
    assert ResponseLog.objects.count() == 0
    assert GenerationEvent.objects.count() == 1


@pytest.mark.django_db
def test_prune_logs_command_zero_retention_skips_table(persona_no, settings):
    settings.RESPONSE_LOG_RETENTION_DAYS = 0  # keep forever
    settings.GENERATION_EVENT_RETENTION_DAYS = 90
    _log(persona_no, age_days=500)
    _event(persona_no, age_days=500)
    call_command("prune_logs")
    assert ResponseLog.objects.count() == 1  # skipped
    assert GenerationEvent.objects.count() == 0


@pytest.mark.django_db
def test_prune_logs_command_all_disabled(persona_no, settings):
    settings.RESPONSE_LOG_RETENTION_DAYS = 0
    settings.GENERATION_EVENT_RETENTION_DAYS = 0
    _log(persona_no, age_days=500)
    _event(persona_no, age_days=500)
    call_command("prune_logs")
    assert ResponseLog.objects.count() == 1
    assert GenerationEvent.objects.count() == 1
