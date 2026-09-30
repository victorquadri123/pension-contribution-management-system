import random
from datetime import date
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel

class CustomUserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier for auth."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', CustomUser.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        MEMBER = 'MEMBER', 'Member / Contributor'
        ADMIN = 'ADMIN', 'Admin / PFA Officer'

    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, default='')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.email})" if full_name else self.email


class Member(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        RETIRED = 'RETIRED', 'Retired'

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile'
    )
    employer = models.ForeignKey(
        'employers.Employer',
        on_delete=models.PROTECT,
        related_name='members',
        null=True,
        blank=True
    )
    rsa_pin = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Retirement Savings Account PIN (e.g., PEN100847291034)"
    )
    nin = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        help_text="National Identification Number (11 digits)"
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True)
    address = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_onboarded = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Member'
        verbose_name_plural = 'Members'

    def __str__(self):
        pin_str = f" - {self.rsa_pin}" if self.rsa_pin else ""
        return f"{self.user.get_full_name()} ({self.user.email}){pin_str}"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.email

    @property
    def email(self):
        return self.user.email

    @property
    def phone_number(self):
        return self.user.phone_number

    def calculate_age(self, as_of=None):
        if not self.date_of_birth:
            return None
        today = as_of or date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def clean(self):
        super().clean()
        if self.date_of_birth:
            age = self.calculate_age()
            if age is not None:
                if age < 18:
                    raise ValidationError({'date_of_birth': _('Member must be at least 18 years old.')})
                if age > 70:
                    raise ValidationError({'date_of_birth': _('Member age cannot exceed 70 years.')})

    def save(self, *args, **kwargs):
        self.clean()
        if not self.rsa_pin and self.is_onboarded:
            self.rsa_pin = self.generate_unique_rsa_pin()
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_rsa_pin(cls):
        """Generate a realistic 12-digit RSA PIN starting with PEN10..."""
        while True:
            suffix = ''.join(str(random.randint(0, 9)) for _ in range(8))
            pin = f"PEN10{suffix}"
            if not cls.all_objects.filter(rsa_pin=pin).exists():
                return pin
