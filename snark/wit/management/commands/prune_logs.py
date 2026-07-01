from django.core.management.base import BaseCommand
from wit.maintenance import prune_response_logs


class Command(BaseCommand):
    help = "Delete ResponseLog rows older than --days days (default 90)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)

    def handle(self, *args, **options):
        days = options["days"]
        count = prune_response_logs(days)
        self.stdout.write(
            self.style.SUCCESS(
                f"Pruned {count} response log(s) older than {days} days."
            )
        )
