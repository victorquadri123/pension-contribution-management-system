from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from apps.employers.services import EmployerService
from apps.members.services import MemberService
from apps.members.models import Member
from apps.contributions.models import Contribution
from apps.contributions.services import ContributionService

@pytest.fixture
def onboarded_member(db):
    employer = EmployerService.register_employer(
        company_name="Nigerian Breweries Plc",
        registration_number="RC-NB-001",
        email="pensions@nbplc.com",
        phone_number="08012345678"
    )
    user, member = MemberService.register_user(
        email="contributor.test@example.com",
        password="Password123",
        first_name="Emeka",
        last_name="Nnamdi"
    )
    return MemberService.complete_onboarding(
        member=member,
        date_of_birth=date(1992, 4, 10),
        nin="22334455667",
        employer_id=employer.id,
        gender=Member.Gender.MALE
    )

@pytest.mark.django_db
class TestContributions:
    def test_record_monthly_contribution(self, onboarded_member):
        c = ContributionService.record_contribution(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('50000.00'),
            contribution_year=2025,
            contribution_month=1
        )
        assert c.id is not None
        assert c.amount == Decimal('50000.00')
        assert c.status == Contribution.Status.PENDING

    def test_duplicate_monthly_contribution_in_same_month_rejected(self, onboarded_member):
        # 1st monthly contribution
        ContributionService.record_contribution(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('50000.00'),
            contribution_year=2025,
            contribution_month=2
        )
        # Attempt 2nd monthly contribution for same month
        with pytest.raises(ValidationError) as exc:
            ContributionService.record_contribution(
                member=onboarded_member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                amount=Decimal('45000.00'),
                contribution_year=2025,
                contribution_month=2
            )
        assert 'contribution_type' in exc.value.message_dict

    def test_multiple_voluntary_contributions_allowed_in_same_month(self, onboarded_member):
        v1 = ContributionService.record_contribution(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.VOLUNTARY,
            amount=Decimal('20000.00'),
            contribution_year=2025,
            contribution_month=2
        )
        v2 = ContributionService.record_contribution(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.VOLUNTARY,
            amount=Decimal('35000.00'),
            contribution_year=2025,
            contribution_month=2
        )
        assert v1.id is not None
        assert v2.id is not None
        assert v1.id != v2.id

    def test_amount_must_be_greater_than_zero(self, onboarded_member):
        with pytest.raises(ValidationError) as exc:
            ContributionService.record_contribution(
                member=onboarded_member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                amount=Decimal('0.00'),
                contribution_year=2025,
                contribution_month=3
            )
        assert 'amount' in exc.value.message_dict

    def test_future_payment_date_rejected(self, onboarded_member):
        future_date = date.today() + timedelta(days=5)
        with pytest.raises(ValidationError) as exc:
            ContributionService.record_contribution(
                member=onboarded_member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                amount=Decimal('50000.00'),
                contribution_year=2025,
                contribution_month=3,
                payment_date=future_date
            )
        assert 'payment_date' in exc.value.message_dict

    def test_statement_generation(self, onboarded_member):
        # Create 2 validated contributions
        c1 = Contribution.objects.create(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('50000.00'),
            contribution_year=2025,
            contribution_month=1,
            payment_date=date(2025, 1, 28),
            status=Contribution.Status.VALIDATED
        )
        c2 = Contribution.objects.create(
            member=onboarded_member,
            contribution_type=Contribution.ContributionType.VOLUNTARY,
            amount=Decimal('25000.00'),
            contribution_year=2025,
            contribution_month=1,
            payment_date=date(2025, 1, 30),
            status=Contribution.Status.VALIDATED
        )

        statement = ContributionService.generate_statement(
            member=onboarded_member,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )

        assert statement['period_monthly'] == Decimal('50000.00')
        assert statement['period_voluntary'] == Decimal('25000.00')
        assert statement['period_contributions_total'] == Decimal('75000.00')
        assert statement['closing_balance'] == Decimal('75000.00')
        assert len(statement['transactions']) == 2
