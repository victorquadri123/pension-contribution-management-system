from datetime import date
from decimal import Decimal
from rest_framework import serializers
from apps.contributions.models import Contribution
from apps.members.models import Member

class ContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    rsa_pin = serializers.CharField(source='member.rsa_pin', read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.filter(is_deleted=False),
        source='member'
    )

    class Meta:
        model = Contribution
        fields = [
            'id', 'member_id', 'member_name', 'rsa_pin', 'contribution_type',
            'amount', 'contribution_year', 'contribution_month', 'payment_date',
            'transaction_reference', 'status', 'failure_reason', 'validated_at',
            'created_at'
        ]
        read_only_fields = ['id', 'transaction_reference', 'status', 'failure_reason', 'validated_at', 'created_at']

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Contribution amount must be strictly greater than 0.")
        return value

    def validate_contribution_month(self, value):
        if not (1 <= value <= 12):
            raise serializers.ValidationError("Contribution month must be between 1 and 12.")
        return value

    def validate_payment_date(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Contribution payment date cannot be in the future.")
        return value

    def validate(self, data):
        c_type = data.get('contribution_type')
        member = data.get('member')
        year = data.get('contribution_year')
        month = data.get('contribution_month')

        if c_type == Contribution.ContributionType.MONTHLY and member:
            existing = Contribution.objects.filter(
                member=member,
                contribution_type=Contribution.ContributionType.MONTHLY,
                contribution_year=year,
                contribution_month=month,
                is_deleted=False
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise serializers.ValidationError({
                    'contribution_type': (
                        f"A monthly contribution for {month}/{year} already exists for this member. "
                        f"Additional payments in this period must be recorded as Voluntary Contributions."
                    )
                })
        return data


class StatementRequestSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
