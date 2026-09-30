from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.members.models import Member
from apps.members.serializers import (
    MemberSerializer,
    MemberRegistrationSerializer,
    MemberOnboardingSerializer
)
from apps.members.services import MemberService

class MemberViewSet(viewsets.ModelViewSet):
    """
    API for Member Management:
    - Register: POST /api/v1/members/register/
    - Onboard: POST /api/v1/members/{id}/onboard/
    - List / Retrieve / Update members
    - Soft delete: DELETE /api/v1/members/{id}/
    - Restore: POST /api/v1/members/{id}/restore/
    """
    queryset = Member.objects.select_related('user', 'employer').all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'rsa_pin', 'nin']
    ordering_fields = ['created_at', 'rsa_pin']

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = MemberRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, member = MemberService.register_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            phone_number=serializer.validated_data.get('phone_number', '')
        )
        return Response(
            MemberSerializer(member).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='onboard')
    def onboard(self, request, pk=None):
        member = self.get_object()
        serializer = MemberOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            member = MemberService.complete_onboarding(
                member=member,
                date_of_birth=serializer.validated_data['date_of_birth'],
                nin=serializer.validated_data['nin'],
                employer_id=serializer.validated_data['employer_id'],
                gender=serializer.validated_data.get('gender'),
                address=serializer.validated_data.get('address', '')
            )
            return Response(MemberSerializer(member).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        # Soft delete
        instance.delete()

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        try:
            member = Member.all_objects.get(pk=pk)
            member.restore()
            return Response({'status': 'Member restored successfully.'}, status=status.HTTP_200_OK)
        except Member.DoesNotExist:
            return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
