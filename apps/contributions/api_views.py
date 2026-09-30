from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.contributions.models import Contribution
from apps.contributions.serializers import ContributionSerializer, StatementRequestSerializer
from apps.contributions.services import ContributionService
from apps.members.models import Member

class ContributionViewSet(viewsets.ModelViewSet):
    """
    API for Contribution Processing:
    - List / Retrieve contributions
    - Record new contribution (Monthly or Voluntary)
    - GET /api/v1/contributions/statement/?member_id=X&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    - GET /api/v1/contributions/summary/?member_id=X
    """
    queryset = Contribution.objects.select_related('member', 'member__user').all()
    serializer_class = ContributionSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['transaction_reference', 'member__user__first_name', 'member__user__last_name', 'member__rsa_pin']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-payment_date', '-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        member_id = self.request.query_params.get('member_id')
        status_param = self.request.query_params.get('status')
        type_param = self.request.query_params.get('type')

        if member_id:
            qs = qs.filter(member_id=member_id)
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if type_param:
            qs = qs.filter(contribution_type=type_param.upper())
        return qs

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        member_id = request.query_params.get('member_id')
        if not member_id:
            return Response({'error': 'member_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

        totals = ContributionService.get_member_totals(member)
        return Response(totals)

    @action(detail=False, methods=['get'], url_path='statement')
    def statement(self, request):
        serializer = StatementRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            member = Member.objects.get(pk=serializer.validated_data['member_id'])
        except Member.DoesNotExist:
            return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

        statement_data = ContributionService.generate_statement(
            member=member,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )

        return Response({
            'member_id': member.id,
            'member_name': member.full_name,
            'rsa_pin': member.rsa_pin,
            'start_date': statement_data['start_date'],
            'end_date': statement_data['end_date'],
            'opening_balance': statement_data['opening_balance'],
            'period_monthly_contributions': statement_data['period_monthly'],
            'period_voluntary_contributions': statement_data['period_voluntary'],
            'period_total_contributions': statement_data['period_contributions_total'],
            'period_total_interest': statement_data['period_interest_total'],
            'closing_balance': statement_data['closing_balance'],
            'transactions_count': len(statement_data['transactions']),
            'transactions': statement_data['transactions']
        })
