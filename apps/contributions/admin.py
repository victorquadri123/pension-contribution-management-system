from django.contrib import admin
from apps.contributions.models import Contribution

@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('transaction_reference', 'member', 'contribution_type', 'amount', 'contribution_month', 'contribution_year', 'status', 'payment_date')
    search_fields = ('transaction_reference', 'member__rsa_pin', 'member__user__email')
    list_filter = ('contribution_type', 'status', 'contribution_year')
