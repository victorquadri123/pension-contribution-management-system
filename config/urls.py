from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.members import web_views as member_views
from apps.contributions import web_views as contribution_views
from apps.jobs import web_views as job_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Web UI Authentication & Onboarding
    path('', lambda request: redirect('dashboard'), name='home'),
    path('login/', member_views.login_view, name='login'),
    path('signup/', member_views.signup_view, name='signup'),
    path('logout/', member_views.logout_view, name='logout'),
    path('onboarding/', member_views.onboarding_view, name='onboarding'),

    # Contributor Portal
    path('dashboard/', member_views.dashboard_view, name='dashboard'),
    path('profile/', member_views.profile_view, name='profile'),
    path('contributions/', contribution_views.contributions_list_view, name='contributions_list'),
    path('contributions/new/', contribution_views.make_contribution_view, name='make_contribution'),
    path('statement/', contribution_views.statement_view, name='statement'),

    # PFA Operations & Background Jobs Dashboard
    path('portal/', job_views.admin_portal_view, name='admin_portal'),
    path('portal/jobs/validate/', job_views.trigger_validation_job_view, name='trigger_validation_job'),
    path('portal/jobs/interest/', job_views.trigger_interest_job_view, name='trigger_interest_job'),
    path('portal/jobs/retry/', job_views.trigger_retry_job_view, name='trigger_retry_job'),
    path('portal/members/<int:member_id>/toggle-delete/', job_views.soft_delete_member_toggle_view, name='toggle_soft_delete_member'),

    # RESTful API Endpoints
    path('api/v1/', include('config.api_urls')),

    # Swagger / OpenAPI Interactive Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
