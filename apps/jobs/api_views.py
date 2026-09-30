from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.jobs.models import JobExecutionLog, NotificationLog, InterestAccrual
from apps.jobs.serializers import JobExecutionLogSerializer, NotificationLogSerializer, InterestAccrualSerializer
from apps.jobs.services import BackgroundJobService

class JobManagementViewSet(viewsets.ViewSet):
    """
    API for Background Job Processing & Monitoring:
    - POST /api/v1/jobs/validate-contributions/
    - POST /api/v1/jobs/accrue-interest/
    - POST /api/v1/jobs/retry-failed/
    - GET  /api/v1/jobs/logs/
    - GET  /api/v1/jobs/notifications/
    - GET  /api/v1/jobs/interest-accruals/
    """
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], url_path='validate-contributions')
    def validate_contributions(self, request):
        count = BackgroundJobService.validate_pending_contributions()
        return Response({
            'status': 'success',
            'message': f'Validated {count} pending contributions.',
            'processed_count': count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='accrue-interest')
    def accrue_interest(self, request):
        year = request.data.get('year')
        month = request.data.get('month')
        rate = request.data.get('annual_rate', '10.50')
        count = BackgroundJobService.accrue_monthly_interest(
            year=int(year) if year else None,
            month=int(month) if month else None,
            annual_rate=Decimal(str(rate))
        )
        return Response({
            'status': 'success',
            'message': f'Accrued interest for {count} members.',
            'credited_count': count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='retry-failed')
    def retry_failed(self, request):
        count = BackgroundJobService.retry_failed_transactions()
        return Response({
            'status': 'success',
            'message': f'Retried {count} failed contributions.',
            'retried_count': count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='logs')
    def logs(self, request):
        logs_qs = JobExecutionLog.objects.all()[:50]
        return Response(JobExecutionLogSerializer(logs_qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='notifications')
    def notifications(self, request):
        notifs_qs = NotificationLog.objects.all()[:50]
        return Response(NotificationLogSerializer(notifs_qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='interest-accruals')
    def interest_accruals(self, request):
        accruals_qs = InterestAccrual.objects.select_related('member', 'member__user').all()[:50]
        return Response(InterestAccrualSerializer(accruals_qs, many=True).data)
