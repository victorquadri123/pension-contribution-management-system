from rest_framework import serializers
from apps.benefits.models import BenefitEligibility

class BenefitEligibilitySerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    rsa_pin = serializers.CharField(source='member.rsa_pin', read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = BenefitEligibility
        fields = [
            'id', 'member_id', 'member_name', 'rsa_pin', 'months_contributed',
            'total_contributions_amount', 'total_interest_amount', 'is_eligible',
            'eligibility_type', 'status_notes', 'progress_percentage', 'last_evaluated_at'
        ]
        read_only_fields = fields
