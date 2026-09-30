from datetime import date
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from apps.contributions.models import Contribution

class ContributionForm(forms.ModelForm):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    contribution_month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model = Contribution
        fields = ['contribution_type', 'amount', 'contribution_year', 'contribution_month', 'payment_date']
        widgets = {
            'contribution_type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. 50000.00', 'step': '100.00', 'min': '100'}),
            'contribution_year': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'min': '1990', 'max': '2050'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop('member', None)
        super().__init__(*args, **kwargs)
        today = date.today()
        if not self.initial.get('contribution_year'):
            self.initial['contribution_year'] = today.year
        if not self.initial.get('contribution_month'):
            self.initial['contribution_month'] = today.month
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = today

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0.00'):
            raise ValidationError("Contribution amount must be strictly greater than 0.")
        return amount

    def clean_payment_date(self):
        p_date = self.cleaned_data.get('payment_date')
        if p_date and p_date > date.today():
            raise ValidationError("Payment date cannot be in the future.")
        return p_date

    def clean(self):
        cleaned_data = super().clean()
        c_type = cleaned_data.get('contribution_type')
        year = cleaned_data.get('contribution_year')
        month = cleaned_data.get('contribution_month')

        if c_type == Contribution.ContributionType.MONTHLY and self.member and year and month:
            # Check unique monthly rule
            existing = Contribution.objects.filter(
                member=self.member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                contribution_year=year,
                contribution_month=month,
                is_deleted=False
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError({
                    'contribution_type': (
                        f"A monthly contribution for {month}/{year} has already been recorded for your account. "
                        f"Please select 'Additional Voluntary Contribution (AVC)' if you wish to make extra payments this month."
                    )
                })
        return cleaned_data
