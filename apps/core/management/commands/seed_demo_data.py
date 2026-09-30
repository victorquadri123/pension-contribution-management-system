import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.employers.models import Employer
from apps.members.models import CustomUser, Member
from apps.contributions.models import Contribution
from apps.benefits.models import BenefitEligibility
from apps.jobs.services import BackgroundJobService

class Command(BaseCommand):
    help = 'Seeds initial employers, members, and contribution history for testing and live demo.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data for NLPC PFA EPS+ System...")

        # 1. Superuser / Admin
        for admin_email, admin_fname, admin_pwd in [
            ("victorayomide319@gmail.com", "Victor", "moneySTAND123@"),
            ("admin@nlpcpfa.com", "NLPC", "moneySTAND123@"),
        ]:

            admin_user, created = CustomUser.objects.get_or_create(
                email=admin_email,
                defaults={
                    'first_name': admin_fname,
                    'last_name': 'Administrator',
                    'role': CustomUser.Role.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if created:
                admin_user.set_password(admin_pwd)
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f"Created Admin: {admin_email} / {admin_pwd}"))


        # 2. Employers
        employers_data = [
            ("NLPC PFA Limited", "RC-104928", "info@nlpcpfa.com", "+2348030000001", "312 Herbert Macaulay Way, Yaba, Lagos"),
            ("Dangote Industries Ltd", "RC-203948", "pensions@dangote.com", "+2348030000002", "1 Alfred Rewane Road, Ikoyi, Lagos"),
            ("Zenith Bank Plc", "RC-394820", "remittance@zenithbank.com", "+2348030000003", "Plot 84 Ajose Adeogun, Victoria Island, Lagos"),
            ("MTN Nigeria Communications", "RC-482910", "hr@mtn.ng", "+2348030000004", "Golden Plaza, Falomo, Ikoyi, Lagos"),
        ]

        employer_objs = []
        for name, reg, email, phone, addr in employers_data:
            emp, _ = Employer.objects.get_or_create(
                registration_number=reg,
                defaults={
                    'company_name': name,
                    'email': email,
                    'phone_number': phone,
                    'address': addr,
                    'status': Employer.Status.ACTIVE,
                    'is_active': True
                }
            )
            employer_objs.append(emp)
        self.stdout.write(self.style.SUCCESS(f"Created {len(employer_objs)} Employers."))

        # 3. Contributor Member
        members_seed = [
            {
                'email': 'moneystand123@gmail.com',
                'first_name': 'Money',
                'last_name': 'Stand',
                'phone': '+2348099887766',
                'dob': date(1990, 8, 15),
                'gender': Member.Gender.MALE,
                'nin': '11223344556',
                'employer': employer_objs[0],
                'months_history': 6,
                'salary_contrib': Decimal('50000.00'),
            }
        ]


        for m_data in members_seed:
            user, created = CustomUser.objects.get_or_create(
                email=m_data['email'],
                defaults={
                    'first_name': m_data['first_name'],
                    'last_name': m_data['last_name'],
                    'phone_number': m_data['phone'],
                    'role': CustomUser.Role.MEMBER
                }
            )
            if created:
                user.set_password("moneySTAND123@")
                user.save()


            member, _ = Member.objects.get_or_create(
                user=user,
                defaults={
                    'employer': m_data['employer'],
                    'date_of_birth': m_data['dob'],
                    'gender': m_data['gender'],
                    'nin': m_data['nin'],
                    'address': "Lagos, Nigeria",
                    'is_onboarded': True,
                    'status': Member.Status.ACTIVE
                }
            )
            if not member.is_onboarded:
                member.is_onboarded = True
                member.employer = m_data['employer']
                member.date_of_birth = m_data['dob']
                member.nin = m_data['nin']
                member.save()

            # Seed historical contributions
            today = date.today()
            months = m_data['months_history']
            for i in range(months, 0, -1):
                # Calculate year and month back
                total_months = today.year * 12 + today.month - i
                c_year = total_months // 12
                c_month = total_months % 12
                if c_month == 0:
                    c_month = 12
                    c_year -= 1

                p_date = date(c_year, c_month, 25)
                if p_date > today:
                    p_date = today

                # 1 Mandatory Monthly
                if not Contribution.objects.filter(member=member, contribution_year=c_year, contribution_month=c_month, contribution_type=Contribution.ContributionType.MONTHLY).exists():
                    Contribution.objects.create(
                        member=member,
                        contribution_type=Contribution.ContributionType.MONTHLY,
                        amount=m_data['salary_contrib'],
                        contribution_year=c_year,
                        contribution_month=c_month,
                        payment_date=p_date,
                        status=Contribution.Status.VALIDATED,
                        validated_at=timezone.now()
                    )

                # Occasional Voluntary Contribution (AVC)
                if i % 4 == 0:
                    Contribution.objects.create(
                        member=member,
                        contribution_type=Contribution.ContributionType.VOLUNTARY,
                        amount=Decimal('20000.00'),
                        contribution_year=c_year,
                        contribution_month=c_month,
                        payment_date=p_date,
                        status=Contribution.Status.VALIDATED,
                        validated_at=timezone.now()
                    )

            # Evaluate eligibility
            eligibility, _ = BenefitEligibility.objects.get_or_create(member=member)
            eligibility.evaluate()

        self.stdout.write(self.style.SUCCESS("Members and contributions created."))

        # 4. Run background interest accrual
        BackgroundJobService.accrue_monthly_interest(year=date.today().year, month=date.today().month)

        self.stdout.write(self.style.SUCCESS("Demo database successfully populated!"))
        self.stdout.write(self.style.NOTICE("Test account credentials (all password: moneySTAND123@):"))
        self.stdout.write("  Admin:       victorayomide319@gmail.com | Password: moneySTAND123@")
        self.stdout.write("  Contributor: moneystand123@gmail.com    | Password: moneySTAND123@")
        self.stdout.write("  Admin (Alt): admin@nlpcpfa.com          | Password: moneySTAND123@")

