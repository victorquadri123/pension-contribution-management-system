from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.benefits.models import BenefitEligibility
from apps.benefits.serializers import BenefitEligibilitySerializer

class BenefitEligibilityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for Benefit Eligibility status and recalculation:
    - GET /api/v1/benefits/
    - GET /api/v1/benefits/{id}/
    - POST /api/v1/benefits/{id}/evaluate/
    - POST /api/v1/benefits/evaluate_all/
    """
    queryset = BenefitEligibility.objects.select_related('member', 'member__user').all()
    serializer_class = BenefitEligibilitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        member_id = self.request.query_params.get('member_id')
        is_eligible = self.request.query_params.get('is_eligible')
        if member_id:
            qs = qs.filter(member_id=member_id)
        if is_eligible is not None:
            val = is_eligible.lower() in ['true', '1']
            qs = qs.filter(is_eligible=val)
        return qs

    @action(detail=True, methods=['post'], url_path='evaluate')
    def evaluate(self, request, pk=None):
        instance = self.get_object()
        instance.evaluate()
        return Response(BenefitEligibilitySerializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='evaluate_all')
    def evaluate_all(self, request):
        count = 0
        for item in BenefitEligibility.objects.all():
            item.evaluate()
            count += 1
        return Response({'message': f'Evaluated benefit eligibility for {count} members.'}, status=status.HTTP_200_OK)
