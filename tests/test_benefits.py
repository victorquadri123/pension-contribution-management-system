from datetime import date
from decimal import Decimal
import pytest
from apps.employers.services import EmployerService
from apps.members.services import MemberService
from apps.members.models import Member
from apps.contributions.models import Contribution
from apps.benefits.models import BenefitEligibility

@pytest.mark.django_db
class TestBenefitEligibility:
    def test_ineligible_member(self):
        emp = EmployerService.register_employer(
            company_name="Tech Corp Ltd",
            registration_number="RC-TECH-11",
            email="hr@techcorp.ng",
            phone_number="08099887766"
        )
        user, member = MemberService.register_user(
            email="young.contributor@example.com",
            password="Password123",
            first_name="Kola",
            last_name="Johnson"
        )
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1998, 1, 1), # Age ~27
            nin="33445566778",
            employer_id=emp.id
        )

        eligibility = BenefitEligibility.objects.get(member=member)
        eligibility.evaluate()
        assert eligibility.is_eligible is False
        assert eligibility.eligibility_type == BenefitEligibility.EligibilityType.NONE

    def test_eligible_via_minimum_service_60_months(self):
        emp = EmployerService.register_employer(
            company_name="Fintech Hub Ltd",
            registration_number="RC-FTH-22",
            email="hr@fintech.ng",
            phone_number="08099887755"
        )
        user, member = MemberService.register_user(
            email="longservice@example.com",
            password="Password123",
            first_name="Sola",
            last_name="Ojo"
        )
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1990, 1, 1), # Age ~35 (< 50)
            nin="33445566779",
            employer_id=emp.id
        )

        # Create 60 distinct validated monthly contributions across 5 years
        for i in range(60):
            year = 2019 + (i // 12)
            month = (i % 12) + 1
            Contribution.objects.create(
                member=member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                amount=Decimal('30000.00'),
                contribution_year=year,
                contribution_month=month,
                status=Contribution.Status.VALIDATED,
                payment_date=date(year, month, 25)
            )

        eligibility = BenefitEligibility.objects.get(member=member)
        eligibility.evaluate()
        assert eligibility.is_eligible is True
        assert eligibility.eligibility_type == BenefitEligibility.EligibilityType.MINIMUM_SERVICE
        assert eligibility.months_contributed == 60
        assert eligibility.progress_percentage == 100

    def test_eligible_via_retirement_age(self):
        emp = EmployerService.register_employer(
            company_name="Oil & Gas Plc",
            registration_number="RC-OG-33",
            email="pension@oilgas.ng",
            phone_number="08099887744"
        )
        user, member = MemberService.register_user(
            email="retiree@example.com",
            password="Password123",
            first_name="Elder",
            last_name="Ibrahim"
        )
        # Age ~58 (>= 50)
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1967, 5, 20),
            nin="33445566780",
            employer_id=emp.id
        )
        # 1 validated contribution
        Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('80000.00'),
            contribution_year=2024,
            contribution_month=12,
            status=Contribution.Status.VALIDATED,
            payment_date=date(2024, 12, 20)
        )

        eligibility = BenefitEligibility.objects.get(member=member)
        eligibility.evaluate()
        assert eligibility.is_eligible is True
        assert eligibility.eligibility_type == BenefitEligibility.EligibilityType.RETIREMENT
