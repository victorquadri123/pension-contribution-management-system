from datetime import date
import pytest
from django.core.exceptions import ValidationError
from apps.members.models import CustomUser, Member
from apps.members.services import MemberService
from apps.employers.services import EmployerService

@pytest.fixture
def active_employer(db):
    return EmployerService.register_employer(
        company_name="Dangote Cement Plc",
        registration_number="RC-DAN-101",
        email="pensions@dangote-cement.com",
        phone_number="08022223333"
    )

@pytest.mark.django_db
class TestMemberManagement:
    def test_user_registration_simple(self):
        user, member = MemberService.register_user(
            email="test.contributor@example.com",
            password="StrongPassword123!",
            first_name="Tunde",
            last_name="Bakare",
            phone_number="08030004000"
        )
        assert user.id is not None
        assert user.email == "test.contributor@example.com"
        assert member.is_onboarded is False
        assert member.rsa_pin is None

    def test_complete_onboarding_valid_age(self, active_employer):
        user, member = MemberService.register_user(
            email="onboard.user@example.com",
            password="StrongPassword123!",
            first_name="Folake",
            last_name="Adeyemi"
        )
        # 30 years old
        dob = date(1995, 6, 15)
        onboarded = MemberService.complete_onboarding(
            member=member,
            date_of_birth=dob,
            nin="12345678901",
            employer_id=active_employer.id,
            gender=Member.Gender.FEMALE,
            address="15 Marina, Lagos"
        )
        assert onboarded.is_onboarded is True
        assert onboarded.rsa_pin is not None
        assert onboarded.rsa_pin.startswith("PEN10")
        assert onboarded.calculate_age() >= 18

    def test_onboarding_underage_rejected(self, active_employer):
        user, member = MemberService.register_user(
            email="underage@example.com",
            password="Password123",
            first_name="Young",
            last_name="Lad"
        )
        # 16 years old
        today = date.today()
        dob = date(today.year - 16, today.month, today.day)
        with pytest.raises(ValidationError) as exc:
            MemberService.complete_onboarding(
                member=member,
                date_of_birth=dob,
                nin="11122233344",
                employer_id=active_employer.id
            )
        assert 'date_of_birth' in exc.value.message_dict

    def test_onboarding_overage_rejected(self, active_employer):
        user, member = MemberService.register_user(
            email="overage@example.com",
            password="Password123",
            first_name="Elder",
            last_name="Man"
        )
        # 75 years old
        today = date.today()
        dob = date(today.year - 75, today.month, today.day)
        with pytest.raises(ValidationError) as exc:
            MemberService.complete_onboarding(
                member=member,
                date_of_birth=dob,
                nin="11122233355",
                employer_id=active_employer.id
            )
        assert 'date_of_birth' in exc.value.message_dict

    def test_invalid_nin_length_rejected(self, active_employer):
        user, member = MemberService.register_user(
            email="badnin@example.com",
            password="Password123",
            first_name="Test",
            last_name="User"
        )
        with pytest.raises(ValidationError) as exc:
            MemberService.complete_onboarding(
                member=member,
                date_of_birth=date(1990, 1, 1),
                nin="12345", # only 5 digits
                employer_id=active_employer.id
            )
        assert 'nin' in exc.value.message_dict

    def test_soft_delete_and_restore_member(self):
        user, member = MemberService.register_user(
            email="delete.me@example.com",
            password="Password123",
            first_name="Delete",
            last_name="Target"
        )
        member_id = member.id
        assert Member.objects.filter(id=member_id).exists()

        # Soft delete
        MemberService.soft_delete_member(member_id)
        assert not Member.objects.filter(id=member_id).exists()
        assert Member.all_objects.filter(id=member_id).exists()

        # Restore
        member_deleted = Member.all_objects.get(id=member_id)
        member_deleted.restore()
        assert Member.objects.filter(id=member_id).exists()
