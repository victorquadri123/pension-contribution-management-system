from rest_framework import viewsets, permissions, filters
from apps.employers.models import Employer
from apps.employers.serializers import EmployerSerializer

class EmployerViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Employers:
    Register, update, retrieve, and delete employers.
    """
    queryset = Employer.objects.all()
    serializer_class = EmployerSerializer
    permission_classes = [permissions.AllowAny] # In test/demo, allow easy testing
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['company_name', 'registration_number', 'email']
    ordering_fields = ['company_name', 'created_at']
    ordering = ['company_name']
