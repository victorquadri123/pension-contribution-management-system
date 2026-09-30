from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.employers.models import Employer

class EmployerService:
    @staticmethod
    def register_employer(company_name, registration_number, email, phone_number, address=""):
        registration_number = registration_number.strip().upper()
        if Employer.all_objects.filter(registration_number=registration_number).exists():
            raise ValidationError({'registration_number': _('An employer with this registration number already exists.')})

        employer = Employer.objects.create(
            company_name=company_name.strip(),
            registration_number=registration_number,
            email=email.strip().lower(),
            phone_number=phone_number.strip(),
            address=address.strip(),
            status=Employer.Status.ACTIVE,
            is_active=True
        )
        return employer

    @staticmethod
    def get_active_employers():
        return Employer.objects.filter(is_active=True, status=Employer.Status.ACTIVE)
