from django.conf import settings
from django.core.management.base import BaseCommand
from wit.maintenance import prune_generation_events, prune_response_logs


class Command(BaseCommand):
    help = (
        "Delete ResponseLog + GenerationEvent rows past their retention. With "
        "--days, applies that window to both; otherwise uses "
        "RESPONSE_LOG_RETENTION_DAYS / GENERATION_EVENT_RETENTION_DAYS (0 = keep)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None)

    def handle(self, *args, **options):
        override = options["days"]
        log_days = (
            override if override is not None else settings.RESPONSE_LOG_RETENTION_DAYS
        )
        event_days = (
            override
            if override is not None
            else settings.GENERATION_EVENT_RETENTION_DAYS
        )
        logs = prune_response_logs(log_days) if log_days > 0 else 0
        events = prune_generation_events(event_days) if event_days > 0 else 0
        if log_days <= 0 and event_days <= 0:
            self.stdout.write("Retention disabled; nothing pruned.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Pruned {logs} response log(s) (>{log_days}d) and "
                f"{events} event(s) (>{event_days}d)."
            )
        )
