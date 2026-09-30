from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from apps.contributions.models import Contribution
from apps.members.models import Member
from apps.benefits.models import BenefitEligibility
from apps.jobs.models import InterestAccrual, JobExecutionLog, NotificationLog

class BackgroundJobService:
    @classmethod
    @transaction.atomic
    def validate_pending_contributions(cls):
        """
        Validates pending contributions against employer status and member status.
        Sends notifications for validated or failed items and updates benefit eligibility.
        """
        job_log = JobExecutionLog.objects.create(
            job_name="Validate Pending Contributions",
            status=JobExecutionLog.Status.RUNNING,
            started_at=timezone.now()
        )

        pending_items = Contribution.objects.filter(status=Contribution.Status.PENDING, is_deleted=False)
        processed_count = 0
        affected_members = set()

        for c in pending_items:
            processed_count += 1
            member = c.member
            employer = member.employer

            # Validation Rule 1: Member must be active
            if member.status != Member.Status.ACTIVE or member.is_deleted:
                c.status = Contribution.Status.FAILED
                c.failure_reason = "Member account is inactive, suspended, or deleted."
                c.save(update_fields=['status', 'failure_reason', 'updated_at'])
                NotificationLog.objects.create(
                    recipient_email=member.email,
                    recipient_name=member.full_name,
                    notification_type=NotificationLog.NotificationType.CONTRIBUTION_FAILED,
                    subject="Contribution Failed - Inactive Member",
                    message=f"Contribution {c.transaction_reference} for ₦{c.amount:,.2f} failed: {c.failure_reason}"
                )
                continue

            # Validation Rule 2: Employer must be active
            if not employer or not employer.is_eligible_for_remittance:
                c.status = Contribution.Status.FAILED
                c.failure_reason = "Remitting employer is not active or is suspended."
                c.save(update_fields=['status', 'failure_reason', 'updated_at'])
                NotificationLog.objects.create(
                    recipient_email=member.email,
                    recipient_name=member.full_name,
                    notification_type=NotificationLog.NotificationType.CONTRIBUTION_FAILED,
                    subject="Contribution Failed - Inactive Employer",
                    message=f"Contribution {c.transaction_reference} for ₦{c.amount:,.2f} failed: {c.failure_reason}"
                )
                continue

            # Validation Success
            c.status = Contribution.Status.VALIDATED
            c.validated_at = timezone.now()
            c.failure_reason = ""
            c.save(update_fields=['status', 'validated_at', 'failure_reason', 'updated_at'])
            affected_members.add(member)

            NotificationLog.objects.create(
                recipient_email=member.email,
                recipient_name=member.full_name,
                notification_type=NotificationLog.NotificationType.CONTRIBUTION_VALIDATED,
                subject="Contribution Validated Successfully",
                message=(
                    f"Your {c.get_contribution_type_display()} of ₦{c.amount:,.2f} "
                    f"({c.transaction_reference}) has been validated and credited to your RSA."
                )
            )

        # Trigger benefit eligibility updates for all affected members
        for member in affected_members:
            eligibility, _ = BenefitEligibility.objects.get_or_create(member=member)
            eligibility.evaluate()

        job_log.status = JobExecutionLog.Status.SUCCESS
        job_log.items_processed = processed_count
        job_log.details = f"Successfully evaluated {processed_count} pending contributions."
        job_log.completed_at = timezone.now()
        job_log.save()

        return processed_count

    @classmethod
    @transaction.atomic
    def accrue_monthly_interest(cls, year=None, month=None, annual_rate=Decimal('10.50')):
        """
        Calculates and credits monthly ROI/interest to active members' RSA balances.
        """
        today = date.today()
        year = year or today.year
        month = month or today.month

        job_log = JobExecutionLog.objects.create(
            job_name=f"Accrue Monthly Interest ({month}/{year})",
            status=JobExecutionLog.Status.RUNNING,
            started_at=timezone.now()
        )

        # Monthly interest rate = (Annual Rate / 12) / 100
        monthly_rate_factor = (annual_rate / Decimal('100')) / Decimal('12')

        active_members = Member.objects.filter(is_onboarded=True, is_deleted=False)
        credited_count = 0

        for member in active_members:
            # Check if active interest for this period has already been applied
            existing = InterestAccrual.all_objects.filter(member=member, year=year, month=month).first()
            if existing:
                if existing.is_deleted:
                    existing.hard_delete()
                else:
                    continue

            # Calculate total current validated contributions + previous interest
            from apps.contributions.services import ContributionService
            totals = ContributionService.get_member_totals(member)
            principal = totals['total_rsa_balance']

            if principal <= Decimal('0.00'):
                continue

            interest_amount = (principal * monthly_rate_factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            closing_balance = principal + interest_amount

            InterestAccrual.objects.create(
                member=member,
                year=year,
                month=month,
                principal_balance=principal,
                annual_rate_percent=annual_rate,
                interest_amount=interest_amount,
                closing_balance=closing_balance,
                applied_at=timezone.now()
            )

            NotificationLog.objects.create(
                recipient_email=member.email,
                recipient_name=member.full_name,
                notification_type=NotificationLog.NotificationType.INTEREST_CREDITED,
                subject=f"Monthly Interest Credited - {month}/{year}",
                message=(
                    f"₦{interest_amount:,.2f} interest has been credited to your RSA "
                    f"for {month}/{year} at an annualized return rate of {annual_rate}%."
                )
            )

            credited_count += 1

            # Update benefit eligibility totals
            eligibility, _ = BenefitEligibility.objects.get_or_create(member=member)
            eligibility.evaluate()

        job_log.status = JobExecutionLog.Status.SUCCESS
        job_log.items_processed = credited_count
        job_log.details = f"Credited monthly interest to {credited_count} member accounts for {month}/{year}."
        job_log.completed_at = timezone.now()
        job_log.save()

        return credited_count

    @classmethod
    def retry_failed_transactions(cls):
        """Retries failed contributions if reasons have been resolved."""
        failed_items = Contribution.objects.filter(status=Contribution.Status.FAILED, is_deleted=False)
        reset_count = 0
        for item in failed_items:
            # If member and employer are active, re-enqueue for validation
            if item.member.status == Member.Status.ACTIVE and item.member.employer and item.member.employer.is_eligible_for_remittance:
                item.status = Contribution.Status.PENDING
                item.failure_reason = "Re-enqueued for validation by retry mechanism."
                item.save(update_fields=['status', 'failure_reason', 'updated_at'])
                reset_count += 1

        if reset_count > 0:
            cls.validate_pending_contributions()

        return reset_count
