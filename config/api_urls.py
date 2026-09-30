from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.employers.api_views import EmployerViewSet
from apps.members.api_views import MemberViewSet
from apps.contributions.api_views import ContributionViewSet
from apps.benefits.api_views import BenefitEligibilityViewSet
from apps.jobs.api_views import JobManagementViewSet

router = DefaultRouter()
router.register(r'employers', EmployerViewSet, basename='api-employers')
router.register(r'members', MemberViewSet, basename='api-members')
router.register(r'contributions', ContributionViewSet, basename='api-contributions')
router.register(r'benefits', BenefitEligibilityViewSet, basename='api-benefits')
router.register(r'jobs', JobManagementViewSet, basename='api-jobs')

urlpatterns = [
    path('', include(router.urls)),
]
