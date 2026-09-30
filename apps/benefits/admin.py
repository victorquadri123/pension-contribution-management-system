from django.contrib import admin
from apps.benefits.models import BenefitEligibility

@admin.register(BenefitEligibility)
class BenefitEligibilityAdmin(admin.ModelAdmin):
    list_display = ('member', 'months_contributed', 'total_contributions_amount', 'is_eligible', 'eligibility_type')
    search_fields = ('member__rsa_pin', 'member__user__email')
    list_filter = ('is_eligible', 'eligibility_type')
