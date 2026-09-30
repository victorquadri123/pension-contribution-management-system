from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.employers.models import Employer
from apps.members.models import Member, CustomUser
from apps.contributions.models import Contribution
from apps.jobs.models import JobExecutionLog, NotificationLog, InterestAccrual
from apps.jobs.services import BackgroundJobService

def is_admin_or_staff(user):
    return user.is_authenticated and (user.role == CustomUser.Role.ADMIN or user.is_staff or user.is_superuser)

def render_admin_404(request):
    """Returns a realistic 404 Not Found page to hide admin endpoint existence."""
    return render(request, '404.html', {'request': request}, status=404)

def admin_portal_view(request):
    # If not admin or unauthenticated, hide endpoint completely with 404 Not Found
    if not is_admin_or_staff(request.user):
        return render_admin_404(request)

    members_qs = Member.all_objects.select_related('user', 'employer').order_by('-created_at')
    employers_qs = Employer.all_objects.all().order_by('company_name')
    pending_contributions_count = Contribution.objects.filter(status=Contribution.Status.PENDING, is_deleted=False).count()
    failed_contributions_count = Contribution.objects.filter(status=Contribution.Status.FAILED, is_deleted=False).count()
    job_logs = JobExecutionLog.objects.all().order_by('-started_at')[:15]
    notification_logs = NotificationLog.objects.all().order_by('-sent_at')[:15]

    total_validated_contributions = sum(
        c.amount for c in Contribution.objects.filter(status=Contribution.Status.VALIDATED, is_deleted=False)
    )
    total_interest = sum(i.interest_amount for i in InterestAccrual.objects.all())
    fum = total_validated_contributions + total_interest

    context = {
        'members': members_qs,
        'employers': employers_qs,
        'pending_count': pending_contributions_count,
        'failed_count': failed_contributions_count,
        'job_logs': job_logs,
        'notifications': notification_logs,
        'fum': fum,
    }
    return render(request, 'admin_portal/dashboard.html', context)


def trigger_validation_job_view(request):
    if not is_admin_or_staff(request.user):
        return render_admin_404(request)

    count = BackgroundJobService.validate_pending_contributions()
    messages.success(request, f"Background Validation Job executed! Processed {count} pending contributions.")
    return redirect('admin_portal')


def trigger_interest_job_view(request):
    if not is_admin_or_staff(request.user):
        return render_admin_404(request)

    from datetime import date
    today = date.today()
    try:
        count = BackgroundJobService.accrue_monthly_interest()
        if count > 0:
            messages.success(
                request,
                f"Monthly Interest Accrual completed! Credited returns to {count} account(s) for {today.strftime('%B %Y')}."
            )
        else:
            already_applied = InterestAccrual.objects.filter(year=today.year, month=today.month).exists()
            if already_applied:
                messages.info(
                    request,
                    f"Interest for {today.strftime('%B %Y')} has already been applied. Monthly interest compounds once per calendar month."
                )
            else:
                messages.warning(
                    request,
                    "No active member accounts with a positive balance found to accrue interest on."
                )
    except Exception as e:
        messages.error(request, f"Error processing interest accrual: {str(e)}")

    return redirect('admin_portal')


def trigger_retry_job_view(request):
    if not is_admin_or_staff(request.user):
        return render_admin_404(request)

    count = BackgroundJobService.retry_failed_transactions()
    messages.success(request, f"Retry Failed Transactions Job executed! Retried {count} items.")
    return redirect('admin_portal')


def soft_delete_member_toggle_view(request, member_id):
    if not is_admin_or_staff(request.user):
        return render_admin_404(request)

    try:
        member = Member.all_objects.get(pk=member_id)
        if member.is_deleted:
            member.restore()
            messages.success(request, f"Member {member.full_name} ({member.rsa_pin}) restored.")
        else:
            member.delete()
            messages.warning(request, f"Member {member.full_name} ({member.rsa_pin}) soft-deleted.")
    except Member.DoesNotExist:
        messages.error(request, "Member not found.")

    return redirect('admin_portal')
