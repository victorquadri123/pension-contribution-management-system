from django.db import models
from apps.core.models import BaseModel

class Employer(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        INACTIVE = 'INACTIVE', 'Inactive'

    company_name = models.CharField(max_length=255, db_index=True)
    registration_number = models.CharField(max_length=50, unique=True, help_text="Official CAC / RC Registration Number")
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['company_name']
        verbose_name = 'Employer'
        verbose_name_plural = 'Employers'

    def __str__(self):
        return f"{self.company_name} ({self.registration_number})"

    @property
    def is_eligible_for_remittance(self):
        return self.is_active and self.status == self.Status.ACTIVE and not self.is_deleted
