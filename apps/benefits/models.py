from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel

class BenefitEligibility(BaseModel):
    class EligibilityType(models.TextChoices):
        NONE = 'NONE', 'Not Yet Eligible'
        MINIMUM_SERVICE = 'MINIMUM_SERVICE', 'Minimum Contribution Period (60 Months / 5 Years)'
        RETIREMENT = 'RETIREMENT', 'Retirement Age Qualified (50+ Years)'
        SPECIAL = 'SPECIAL', 'Special Exemption Approved'

    # Nigerian Pension Reform Act (PRA 2014) standard threshold
    MINIMUM_MONTHS_REQUIRED = 60
    MINIMUM_RETIREMENT_AGE = 50

    member = models.OneToOneField(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='benefit_eligibility'
    )
    months_contributed = models.PositiveIntegerField(default=0)
    total_contributions_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_interest_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    is_eligible = models.BooleanField(default=False, db_index=True)
    eligibility_type = models.CharField(
        max_length=30,
        choices=EligibilityType.choices,
        default=EligibilityType.NONE
    )
    status_notes = models.TextField(blank=True, default='')
    last_evaluated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Benefit Eligibility'
        verbose_name_plural = 'Benefit Eligibilities'

    def __str__(self):
        status = "Eligible" if self.is_eligible else "Ineligible"
        return f"{self.member.full_name} - {status} ({self.months_contributed}/{self.MINIMUM_MONTHS_REQUIRED} months)"

    @property
    def progress_percentage(self):
        """Returns integer 0-100 for progress toward minimum contribution threshold."""
        if self.is_eligible:
            return 100
        return min(100, int((self.months_contributed / self.MINIMUM_MONTHS_REQUIRED) * 100))

    def evaluate(self):
        """
        Evaluates member eligibility based on validated contributions and age criteria.
        """
        from apps.contributions.models import Contribution
        from apps.jobs.models import InterestAccrual

        # Count distinct validated monthly contributions
        validated_contributions = Contribution.objects.filter(
            member=self.member,
            status=Contribution.Status.VALIDATED,
            is_deleted=False
        )

        monthly_count = validated_contributions.filter(
            contribution_type=Contribution.ContributionType.MONTHLY
        ).count()

        total_amount = validated_contributions.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        total_interest = InterestAccrual.objects.filter(
            member=self.member
        ).aggregate(
            total=models.Sum('interest_amount')
        )['total'] or Decimal('0.00')

        self.months_contributed = monthly_count
        self.total_contributions_amount = total_amount
        self.total_interest_amount = total_interest

        age = self.member.calculate_age()

        # Rule 1: Age 50+ (Retirement eligibility) with at least some active contributions
        if age is not None and age >= self.MINIMUM_RETIREMENT_AGE and monthly_count > 0:
            self.is_eligible = True
            self.eligibility_type = self.EligibilityType.RETIREMENT
            self.status_notes = (
                f"Qualified for Retirement Benefits: Member is {age} years old "
                f"(threshold: {self.MINIMUM_RETIREMENT_AGE}) with {monthly_count} validated contribution months."
            )
        # Rule 2: Minimum contribution period (60 months)
        elif monthly_count >= self.MINIMUM_MONTHS_REQUIRED:
            self.is_eligible = True
            self.eligibility_type = self.EligibilityType.MINIMUM_SERVICE
            self.status_notes = (
                f"Qualified via Service Threshold: Completed {monthly_count} "
                f"of {self.MINIMUM_MONTHS_REQUIRED} required monthly contributions."
            )
        else:
            self.is_eligible = False
            self.eligibility_type = self.EligibilityType.NONE
            remaining = self.MINIMUM_MONTHS_REQUIRED - monthly_count
            self.status_notes = (
                f"In progress: {monthly_count}/{self.MINIMUM_MONTHS_REQUIRED} months completed. "
                f"{remaining} more monthly contribution(s) required for vesting."
            )

        self.last_evaluated_at = timezone.now()
        self.save()
        return self
