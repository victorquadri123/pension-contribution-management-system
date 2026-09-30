from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.members.models import CustomUser, Member

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('rsa_pin', 'user', 'employer', 'date_of_birth', 'is_onboarded', 'is_deleted')
    search_fields = ('rsa_pin', 'nin', 'user__email', 'user__first_name', 'user__last_name')
    list_filter = ('is_onboarded', 'gender', 'is_deleted')
