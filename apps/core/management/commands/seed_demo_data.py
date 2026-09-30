from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.employers.models import Employer
from apps.members.models import CustomUser, Member
from apps.contributions.models import Contribution
from apps.benefits.models import BenefitEligibility

class Command(BaseCommand):
    help = 'Seeds authentic employers, members, and real initial state matching the local database.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding real demo data for NLPC PFA EPS+ System...")

        # 1. Superuser / Admin Accounts
        admin_data = [
            ("victorayomide319@gmail.com", "Victor", "Ayomide", "moneySTAND123@", CustomUser.Role.ADMIN),
            ("admin@nlpcpfa.com", "NLPC", "Administrator", "moneySTAND123@", CustomUser.Role.ADMIN),
        ]
        admin_users = {}
        for email, fname, lname, pwd, role in admin_data:
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'role': role,
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            user.set_password(pwd)
            user.is_staff = True
            user.is_superuser = True
            user.role = role
            user.save()
            admin_users[email] = user
            self.stdout.write(self.style.SUCCESS(f"Configured Admin: {email}"))

        # 2. Accredited Employers
        employers_data = [
            ("MTN Nigeria Communications", "RC-482910", "hr@mtn.ng", "+2348030000004", "Golden Plaza, Falomo, Ikoyi, Lagos"),
            ("NLPC PFA Limited", "RC-104928", "info@nlpcpfa.com", "+2348030000001", "312 Herbert Macaulay Way, Yaba, Lagos"),
            ("Dangote Industries Ltd", "RC-203948", "pensions@dangote.com", "+2348030000002", "1 Alfred Rewane Road, Ikoyi, Lagos"),
            ("Zenith Bank Plc", "RC-394820", "remittance@zenithbank.com", "+2348030000003", "Plot 84 Ajose Adeogun, Victoria Island, Lagos"),
        ]

        employer_objs = {}
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
            employer_objs[name] = emp
        self.stdout.write(self.style.SUCCESS(f"Configured {len(employer_objs)} Employers."))

        # 3. Victor Ayomide Member Profile (Onboarded with ₦200,000 contribution yesterday)
        victor_user = admin_users["victorayomide319@gmail.com"]
        victor_member, _ = Member.objects.get_or_create(
            user=victor_user,
            defaults={
                'employer': employer_objs["MTN Nigeria Communications"],
                'rsa_pin': 'PEN1050998995',
                'date_of_birth': date(2004, 5, 1),
                'nin': '34332435333',
                'gender': Member.Gender.MALE,
                'address': '112 ebuwawa road',
                'is_onboarded': True,
                'status': Member.Status.ACTIVE
            }
        )
        # Ensure exact profile values
        victor_member.employer = employer_objs["MTN Nigeria Communications"]
        victor_member.rsa_pin = 'PEN1050998995'
        victor_member.date_of_birth = date(2004, 5, 1)
        victor_member.nin = '34332435333'
        victor_member.gender = Member.Gender.MALE
        victor_member.address = '112 ebuwawa road'
        victor_member.is_onboarded = True
        victor_member.status = Member.Status.ACTIVE
        victor_member.save()

        # Seed Victor's ₦200,000 contribution yesterday
        yesterday = date.today() - timedelta(days=1)
        Contribution.objects.get_or_create(
            transaction_reference='TXN-1517253B536F',
            defaults={
                'member': victor_member,
                'contribution_type': Contribution.ContributionType.MONTHLY,
                'amount': Decimal('200000.00'),
                'contribution_year': yesterday.year,
                'contribution_month': yesterday.month,
                'payment_date': yesterday,
                'status': Contribution.Status.VALIDATED,
                'validated_at': timezone.now()
            }
        )
        victor_eligibility, _ = BenefitEligibility.objects.get_or_create(member=victor_member)
        victor_eligibility.evaluate()
        self.stdout.write(self.style.SUCCESS("Configured Victor Ayomide member profile and ₦200,000 contribution."))

        # 4. Money Stand Member Account (UNVERIFIED / Pending KYC)
        money_user, created = CustomUser.objects.get_or_create(
            email='moneystand123@gmail.com',
            defaults={
                'first_name': 'Money',
                'last_name': 'Stand',
                'role': CustomUser.Role.MEMBER
            }
        )
        money_user.set_password('moneySTAND123@')
        money_user.save()

        money_member, _ = Member.objects.get_or_create(
            user=money_user,
            defaults={
                'is_onboarded': False,
                'status': Member.Status.ACTIVE,
                'rsa_pin': None,
                'employer': None,
                'date_of_birth': None,
                'nin': None,
            }
        )
        # Ensure Money Stand is UNVERIFIED with zero contributions
        money_member.is_onboarded = False
        money_member.rsa_pin = None
        money_member.employer = None
        money_member.date_of_birth = None
        money_member.nin = None
        money_member.save()

        # Delete any accidental dummy contributions for money_member
        Contribution.objects.filter(member=money_member).delete()

        money_eligibility, _ = BenefitEligibility.objects.get_or_create(member=money_member)
        money_eligibility.evaluate()
        self.stdout.write(self.style.SUCCESS("Configured Money Stand as unverified member (zero contributions, KYC pending)."))

        # 5. Additional Demo Account: Kudirat
        kudirat_user, _ = CustomUser.objects.get_or_create(
            email='kudiratkf72@gmail.com',
            defaults={
                'first_name': 'kudirat',
                'last_name': 'folasade',
                'role': CustomUser.Role.MEMBER
            }
        )
        kudirat_user.set_password('moneySTAND123@')
        kudirat_user.save()
        kudirat_member, _ = Member.objects.get_or_create(
            user=kudirat_user,
            defaults={'is_onboarded': False, 'status': Member.Status.ACTIVE}
        )
        kudirat_member.is_onboarded = False
        kudirat_member.save()

        self.stdout.write(self.style.SUCCESS("Demo database successfully synchronized with backend state!"))
        self.stdout.write(self.style.NOTICE("Active account credentials (all password: moneySTAND123@):"))
        self.stdout.write("  Admin:       victorayomide319@gmail.com | ₦200k Contribution (Verified)")
        self.stdout.write("  Contributor: moneystand123@gmail.com    | Pending Setup (Unverified)")
        self.stdout.write("  Admin (Alt): admin@nlpcpfa.com          | Operations Admin")
