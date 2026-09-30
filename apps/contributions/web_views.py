from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.members.models import Member
from apps.contributions.models import Contribution
from apps.contributions.forms import ContributionForm
from apps.contributions.services import ContributionService
from apps.jobs.services import BackgroundJobService

@login_required
def contributions_list_view(request):
    member = get_object_or_404(Member, user=request.user)
    contributions = Contribution.objects.filter(member=member, is_deleted=False).order_by('-payment_date')

    # Optional filter
    c_type = request.GET.get('type')
    status_filter = request.GET.get('status')
    if c_type:
        contributions = contributions.filter(contribution_type=c_type)
    if status_filter:
        contributions = contributions.filter(status=status_filter)

    totals = ContributionService.get_member_totals(member)

    context = {
        'member': member,
        'contributions': contributions,
        'totals': totals,
        'current_type': c_type,
        'current_status': status_filter
    }
    return render(request, 'contributions/list.html', context)


@login_required
def make_contribution_view(request):
    member = get_object_or_404(Member, user=request.user)
    if not member.is_onboarded:
        messages.warning(request, "Please complete your onboarding profile before recording contributions.")
        return redirect('onboarding')

    form = ContributionForm(request.POST or None, member=member)
    if request.method == 'POST' and form.is_valid():
        contribution = form.save(commit=False)
        contribution.member = member
        contribution.status = Contribution.Status.PENDING
        contribution.save()

        # Run automated instant background validation
        BackgroundJobService.validate_pending_contributions()

        # Re-fetch contribution to check updated status
        contribution.refresh_from_db()
        if contribution.status == Contribution.Status.VALIDATED:
            messages.success(
                request,
                f"Contribution of ₦{contribution.amount:,.2f} recorded and successfully validated! Reference: {contribution.transaction_reference}"
            )
        else:
            messages.warning(
                request,
                f"Contribution of ₦{contribution.amount:,.2f} received. Status: {contribution.get_status_display()} ({contribution.failure_reason})"
            )
        return redirect('contributions_list')

    return render(request, 'contributions/create.html', {'form': form, 'member': member})


@login_required
def statement_view(request):
    member = get_object_or_404(Member, user=request.user)
    if not member.is_onboarded:
        messages.warning(request, "Please complete your profile to generate official account statements.")
        return redirect('onboarding')

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = None
    end_date = date.today()

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    statement_data = ContributionService.generate_statement(
        member=member,
        start_date=start_date,
        end_date=end_date
    )

    context = {
        'member': member,
        'statement': statement_data,
        'start_date': start_date,
        'end_date': end_date,
        'now': datetime.now()
    }
    return render(request, 'contributions/statement.html', context)
