"""Response-log retention helpers.

Kept separate from services.py (which is about generation) so both the
``prune_logs`` command and the admin prune actions share one implementation.
"""

from datetime import timedelta

from django.utils import timezone

from .models import GenerationEvent, ResponseLog


def prune_response_logs(days: int) -> int:
    """Delete ResponseLog rows older than ``days``. Returns the count deleted."""
    if days < 0:
        raise ValueError("days must be >= 0")
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = ResponseLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def prune_generation_events(days: int) -> int:
    """Delete GenerationEvent rows older than ``days``. Returns count deleted."""
    if days < 0:
        raise ValueError("days must be >= 0")
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = GenerationEvent.objects.filter(created_at__lt=cutoff).delete()
    return deleted
