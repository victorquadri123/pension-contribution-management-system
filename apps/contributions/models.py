import uuid
from datetime import date
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel

class Contribution(BaseModel):
    class ContributionType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly Mandatory Contribution'
        VOLUNTARY = 'VOLUNTARY', 'Additional Voluntary Contribution (AVC)'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Validation'
        VALIDATED = 'VALIDATED', 'Validated'
        FAILED = 'FAILED', 'Failed'

    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='contributions'
    )
    contribution_type = models.CharField(
        max_length=20,
        choices=ContributionType.choices,
        default=ContributionType.MONTHLY
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    contribution_year = models.PositiveIntegerField()
    contribution_month = models.PositiveIntegerField(
        help_text="Month of contribution (1-12)"
    )
    payment_date = models.DateField(default=date.today)
    transaction_reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    failure_reason = models.TextField(blank=True, default='')
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Contribution'
        verbose_name_plural = 'Contributions'
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'contribution_year', 'contribution_month'],
                condition=models.Q(contribution_type='MONTHLY', is_deleted=False),
                name='unique_monthly_contribution_per_member'
            )
        ]

    def __str__(self):
        return (
            f"{self.member.full_name} | {self.get_contribution_type_display()} | "
            f"₦{self.amount:,.2f} ({self.contribution_month}/{self.contribution_year}) - {self.status}"
        )

    def clean(self):
        super().clean()
        if not self.transaction_reference:
            self.transaction_reference = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        # 1. Amount validation (> 0)
        if self.amount is not None and self.amount <= Decimal('0.00'):
            raise ValidationError({'amount': _('Contribution amount must be strictly greater than 0.')})

        # 2. Valid month check
        if self.contribution_month is not None and not (1 <= self.contribution_month <= 12):
            raise ValidationError({'contribution_month': _('Contribution month must be between 1 and 12.')})

        # 3. Payment date check (cannot be in the future)
        if self.payment_date and self.payment_date > date.today():
            raise ValidationError({'payment_date': _('Contribution payment date cannot be in the future.')})

        # 4. Enforce single monthly contribution per calendar month
        if self.contribution_type == self.ContributionType.MONTHLY and self.member_id:
            existing = Contribution.objects.filter(
                member_id=self.member_id,
                contribution_type=self.ContributionType.MONTHLY,
                contribution_year=self.contribution_year,
                contribution_month=self.contribution_month,
                is_deleted=False
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError({
                    'contribution_type': _(
                        f"A monthly contribution for {self.contribution_month}/{self.contribution_year} "
                        f"already exists for this member. Voluntary contributions can be used for extra payments."
                    )
                })

    def save(self, *args, **kwargs):
        if not self.transaction_reference:
            self.transaction_reference = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        self.clean()
        super().save(*args, **kwargs)
