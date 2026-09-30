from django.core.management.base import BaseCommand
from apps.jobs.services import BackgroundJobService

class Command(BaseCommand):
    help = 'Executes background jobs: contribution validation, interest accruals, and retry logic.'

    def add_arguments(self, parser):
        parser.add_argument('--job', type=str, default='all', choices=['all', 'validate', 'interest', 'retry'])

    def handle(self, *args, **options):
        job = options['job']
        self.stdout.write(self.style.NOTICE(f"Starting background job runner: {job}..."))

        if job in ['all', 'validate']:
            count = BackgroundJobService.validate_pending_contributions()
            self.stdout.write(self.style.SUCCESS(f"Validated {count} pending contributions."))

        if job in ['all', 'interest']:
            count = BackgroundJobService.accrue_monthly_interest()
            self.stdout.write(self.style.SUCCESS(f"Accrued interest for {count} members."))

        if job in ['all', 'retry']:
            count = BackgroundJobService.retry_failed_transactions()
            self.stdout.write(self.style.SUCCESS(f"Retried {count} failed transactions."))

        self.stdout.write(self.style.SUCCESS("All requested background jobs finished successfully."))
