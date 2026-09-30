from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel

class InterestAccrual(BaseModel):
    """
    Records periodic interest / Return on Investment (ROI) credited
    to a contributor's Retirement Savings Account (RSA).
    """
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='interest_accruals'
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    principal_balance = models.DecimalField(max_digits=14, decimal_places=2)
    annual_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.50'))
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    applied_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-year', '-month']
        verbose_name = 'Interest Accrual'
        verbose_name_plural = 'Interest Accruals'
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'year', 'month'],
                condition=models.Q(is_deleted=False),
                name='unique_monthly_interest_per_member'
            )
        ]

    def __str__(self):
        return f"{self.member.full_name} | {self.month}/{self.year} Interest: ₦{self.interest_amount:,.2f}"


class JobExecutionLog(BaseModel):
    class Status(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Completed Successfully'
        FAILED = 'FAILED', 'Failed'

    job_name = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    items_processed = models.PositiveIntegerField(default=0)
    details = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Job Execution Log'
        verbose_name_plural = 'Job Execution Logs'

    def __str__(self):
        return f"{self.job_name} - {self.status} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"


class NotificationLog(BaseModel):
    class NotificationType(models.TextChoices):
        CONTRIBUTION_VALIDATED = 'CONTRIBUTION_VALIDATED', 'Contribution Validated'
        CONTRIBUTION_FAILED = 'CONTRIBUTION_FAILED', 'Contribution Failed / Alert'
        BENEFIT_UPDATE = 'BENEFIT_UPDATE', 'Benefit Eligibility Updated'
        INTEREST_CREDITED = 'INTEREST_CREDITED', 'Interest Credited'

    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_sent = models.BooleanField(default=True)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'

    def __str__(self):
        return f"{self.notification_type} to {self.recipient_email} at {self.sent_at}"
