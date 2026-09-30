from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.members.models import CustomUser, Member
from apps.employers.models import Employer
from apps.benefits.models import BenefitEligibility

class MemberService:
    @staticmethod
    @transaction.atomic
    def register_user(email, password, first_name, last_name, phone_number="", role=CustomUser.Role.MEMBER):
        email = email.strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': _('A user with this email address already exists.')})

        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone_number=phone_number.strip(),
            role=role
        )

        member, _created = Member.objects.get_or_create(user=user)
        # Create initial benefit eligibility record
        BenefitEligibility.objects.get_or_create(member=member)
        return user, member

    @staticmethod
    @transaction.atomic
    def complete_onboarding(member, date_of_birth, nin, employer_id, gender=None, address=""):
        try:
            employer = Employer.objects.get(pk=employer_id, is_active=True, status=Employer.Status.ACTIVE)
        except Employer.DoesNotExist:
            raise ValidationError({'employer': _('Selected employer is not active or does not exist.')})

        # NIN validation: 11 digits
        nin = nin.strip()
        if not nin.isdigit() or len(nin) != 11:
            raise ValidationError({'nin': _('National Identification Number (NIN) must be exactly 11 numeric digits.')})

        member.employer = employer
        member.date_of_birth = date_of_birth
        member.nin = nin
        member.gender = gender
        member.address = address.strip()
        member.is_onboarded = True
        member.status = Member.Status.ACTIVE
        member.full_clean()  # Enforces Age 18-70 validation
        member.save()

        # Initialize benefit eligibility evaluation
        eligibility, _created = BenefitEligibility.objects.get_or_create(member=member)
        eligibility.evaluate()

        return member

    @staticmethod
    def soft_delete_member(member_id):
        try:
            member = Member.objects.get(pk=member_id)
            member.delete()
            return True
        except Member.DoesNotExist:
            raise ValidationError({'member': _('Member not found.')})
