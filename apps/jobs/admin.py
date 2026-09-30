from django.contrib import admin
from apps.jobs.models import InterestAccrual, JobExecutionLog, NotificationLog

@admin.register(InterestAccrual)
class InterestAccrualAdmin(admin.ModelAdmin):
    list_display = ('member', 'month', 'year', 'interest_amount', 'closing_balance', 'applied_at')
    search_fields = ('member__rsa_pin',)
    list_filter = ('year', 'month')

@admin.register(JobExecutionLog)
class JobExecutionLogAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'status', 'items_processed', 'started_at', 'completed_at')
    list_filter = ('status', 'job_name')

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'notification_type', 'subject', 'is_sent', 'sent_at')
    list_filter = ('notification_type', 'is_sent')
