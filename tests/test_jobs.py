from datetime import date
from decimal import Decimal
import pytest
from apps.employers.services import EmployerService
from apps.employers.models import Employer
from apps.members.services import MemberService
from apps.members.models import Member
from apps.contributions.models import Contribution
from apps.jobs.models import JobExecutionLog, NotificationLog, InterestAccrual
from apps.jobs.services import BackgroundJobService

@pytest.fixture
def setup_job_data(db):
    emp = EmployerService.register_employer(
        company_name="Nigerian Ports Authority",
        registration_number="RC-NPA-555",
        email="pensions@npa.gov.ng",
        phone_number="08055554444"
    )
    user, member = MemberService.register_user(
        email="jobtester@example.com",
        password="Password123",
        first_name="Ahmed",
        last_name="Musa"
    )
    MemberService.complete_onboarding(
        member=member,
        date_of_birth=date(1990, 8, 12),
        nin="44556677889",
        employer_id=emp.id
    )
    return emp, member

@pytest.mark.django_db
class TestBackgroundJobs:
    def test_validation_job_success(self, setup_job_data):
        emp, member = setup_job_data

        c = Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('40000.00'),
            contribution_year=2025,
            contribution_month=3,
            status=Contribution.Status.PENDING
        )

        processed = BackgroundJobService.validate_pending_contributions()
        assert processed >= 1

        c.refresh_from_db()
        assert c.status == Contribution.Status.VALIDATED
        assert c.validated_at is not None

        # Verify notification created
        assert NotificationLog.objects.filter(
            recipient_email=member.email,
            notification_type=NotificationLog.NotificationType.CONTRIBUTION_VALIDATED
        ).exists()

    def test_validation_job_fails_when_employer_inactive(self, setup_job_data):
        emp, member = setup_job_data
        emp.status = Employer.Status.SUSPENDED
        emp.save()

        c = Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('40000.00'),
            contribution_year=2025,
            contribution_month=4,
            status=Contribution.Status.PENDING
        )

        BackgroundJobService.validate_pending_contributions()
        c.refresh_from_db()
        assert c.status == Contribution.Status.FAILED
        assert "suspended" in c.failure_reason

    def test_interest_accrual_job(self, setup_job_data):
        emp, member = setup_job_data

        # Give member a validated contribution
        Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('100000.00'),
            contribution_year=2025,
            contribution_month=1,
            status=Contribution.Status.VALIDATED
        )

        # Accrue interest for 2025/1
        count = BackgroundJobService.accrue_monthly_interest(year=2025, month=1, annual_rate=Decimal('12.00'))
        assert count >= 1

        accrual = InterestAccrual.objects.get(member=member, year=2025, month=1)
        # 12% per year = 1% per month. 1% of 100,000 = 1,000
        assert accrual.interest_amount == Decimal('1000.00')
        assert accrual.closing_balance == Decimal('101000.00')

        # Running again in the same month should NOT duplicate interest
        second_run_count = BackgroundJobService.accrue_monthly_interest(year=2025, month=1, annual_rate=Decimal('12.00'))
        assert second_run_count == 0

    def test_retry_failed_transactions(self, setup_job_data):
        emp, member = setup_job_data
        c = Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('25000.00'),
            contribution_year=2025,
            contribution_month=5,
            status=Contribution.Status.FAILED,
            failure_reason="Temporary gateway timeout"
        )
        retried = BackgroundJobService.retry_failed_transactions()
        assert retried >= 1
        c.refresh_from_db()
        assert c.status == Contribution.Status.VALIDATED
