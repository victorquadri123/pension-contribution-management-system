from django.contrib import admin
from apps.employers.models import Employer

@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'registration_number', 'email', 'status', 'is_active')
    search_fields = ('company_name', 'registration_number', 'email')
    list_filter = ('status', 'is_active')
