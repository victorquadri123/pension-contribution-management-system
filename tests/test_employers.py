import pytest
from django.core.exceptions import ValidationError
from apps.employers.models import Employer
from apps.employers.services import EmployerService

@pytest.mark.django_db
class TestEmployer:
    def test_create_valid_employer(self):
        emp = EmployerService.register_employer(
            company_name="Access Bank Plc",
            registration_number="RC-998877",
            email="pension@accessbank.com",
            phone_number="+2348011223344",
            address="Plot 999 Danmole Street, Lagos"
        )
        assert emp.id is not None
        assert emp.registration_number == "RC-998877"
        assert emp.is_active is True
        assert emp.status == Employer.Status.ACTIVE
        assert emp.is_eligible_for_remittance is True

    def test_duplicate_registration_number_raises_error(self):
        EmployerService.register_employer(
            company_name="Company A",
            registration_number="RC-111111",
            email="a@example.com",
            phone_number="08011111111"
        )
        with pytest.raises(ValidationError):
            EmployerService.register_employer(
                company_name="Company B",
                registration_number="RC-111111",
                email="b@example.com",
                phone_number="08022222222"
            )

    def test_inactive_employer_not_eligible(self):
        emp = EmployerService.register_employer(
            company_name="Suspended Co",
            registration_number="RC-222333",
            email="susp@example.com",
            phone_number="08033333333"
        )
        emp.status = Employer.Status.SUSPENDED
        emp.save()
        assert emp.is_eligible_for_remittance is False
