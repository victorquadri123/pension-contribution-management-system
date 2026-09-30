import logging
from datetime import date
from decimal import Decimal
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.contributions.models import Contribution
from apps.jobs.models import InterestAccrual

logger = logging.getLogger('apps.contributions')

class ContributionService:
    @staticmethod
    def record_contribution(member, contribution_type, amount, contribution_year, contribution_month, payment_date=None):
        payment_date = payment_date or date.today()
        amount = Decimal(str(amount))

        contribution = Contribution(
            member=member,
            contribution_type=contribution_type,
            amount=amount,
            contribution_year=contribution_year,
            contribution_month=contribution_month,
            payment_date=payment_date,
            status=Contribution.Status.PENDING
        )
        contribution.full_clean()
        contribution.save()
        cache.delete(f"member_totals_{member.id}")
        logger.info(f"Recorded {contribution_type} contribution of ₦{amount:,.2f} for member {member.rsa_pin}")
        return contribution

    @staticmethod
    def get_member_totals(member, use_cache=True):
        """Calculates validated contribution totals for a member, with caching."""
        cache_key = f"member_totals_{member.id}"
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        validated = Contribution.objects.filter(
            member=member,
            status=Contribution.Status.VALIDATED,
            is_deleted=False
        )

        monthly_total = validated.filter(
            contribution_type=Contribution.ContributionType.MONTHLY
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        voluntary_total = validated.filter(
            contribution_type=Contribution.ContributionType.VOLUNTARY
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        total_contributions = monthly_total + voluntary_total

        total_interest = InterestAccrual.objects.filter(
            member=member
        ).aggregate(total=models.Sum('interest_amount'))['total'] or Decimal('0.00')

        total_rsa_balance = total_contributions + total_interest

        totals = {
            'monthly_total': monthly_total,
            'voluntary_total': voluntary_total,
            'total_contributions': total_contributions,
            'total_interest': total_interest,
            'total_rsa_balance': total_rsa_balance,
            'monthly_count': validated.filter(contribution_type=Contribution.ContributionType.MONTHLY).count(),
            'total_transactions': validated.count(),
        }
        cache.set(cache_key, totals, timeout=60)
        return totals

    @staticmethod
    def generate_statement(member, start_date=None, end_date=None):
        """
        Generates an official Statement of Account for a member with
        Opening Balance, Period Inflows, Accrued Interest, and Closing Balance.
        """
        end_date = end_date or date.today()

        # Prior contributions (Opening Balance)
        prior_contributions_query = Contribution.objects.filter(
            member=member,
            status=Contribution.Status.VALIDATED,
            is_deleted=False
        )
        prior_interest_query = InterestAccrual.objects.filter(member=member)

        if start_date:
            prior_contributions = prior_contributions_query.filter(payment_date__lt=start_date).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            prior_interest = prior_interest_query.filter(applied_at__date__lt=start_date).aggregate(
                total=models.Sum('interest_amount')
            )['total'] or Decimal('0.00')
            opening_balance = prior_contributions + prior_interest
        else:
            opening_balance = Decimal('0.00')

        # Current period records
        period_contributions_qs = Contribution.objects.filter(
            member=member,
            status=Contribution.Status.VALIDATED,
            is_deleted=False,
            payment_date__lte=end_date
        )
        if start_date:
            period_contributions_qs = period_contributions_qs.filter(payment_date__gte=start_date)

        period_interest_qs = InterestAccrual.objects.filter(
            member=member,
            applied_at__date__lte=end_date
        )
        if start_date:
            period_interest_qs = period_interest_qs.filter(applied_at__date__gte=start_date)

        period_monthly = period_contributions_qs.filter(
            contribution_type=Contribution.ContributionType.MONTHLY
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        period_voluntary = period_contributions_qs.filter(
            contribution_type=Contribution.ContributionType.VOLUNTARY
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        period_contributions_total = period_monthly + period_voluntary
        period_interest_total = period_interest_qs.aggregate(
            total=models.Sum('interest_amount')
        )['total'] or Decimal('0.00')

        closing_balance = opening_balance + period_contributions_total + period_interest_total

        # Build combined chronological transaction ledger
        ledger = []
        for c in period_contributions_qs.order_by('payment_date'):
            ledger.append({
                'date': c.payment_date,
                'type': c.get_contribution_type_display(),
                'reference': c.transaction_reference,
                'description': f"Contribution for {c.contribution_month}/{c.contribution_year}",
                'amount': c.amount,
                'category': 'CONTRIBUTION'
            })

        for i in period_interest_qs.order_by('applied_at'):
            ledger.append({
                'date': i.applied_at.date(),
                'type': 'Monthly Interest / ROI',
                'reference': f"INT-{i.year}{i.month:02d}",
                'description': f"Monthly Return ({i.annual_rate_percent}% p.a.)",
                'amount': i.interest_amount,
                'category': 'INTEREST'
            })

        ledger.sort(key=lambda x: x['date'])

        return {
            'member': member,
            'start_date': start_date,
            'end_date': end_date,
            'opening_balance': opening_balance,
            'period_monthly': period_monthly,
            'period_voluntary': period_voluntary,
            'period_contributions_total': period_contributions_total,
            'period_interest_total': period_interest_total,
            'closing_balance': closing_balance,
            'transactions': ledger,
        }
