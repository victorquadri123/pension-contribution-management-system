from rest_framework import serializers
from apps.employers.models import Employer

class EmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employer
        fields = [
            'id', 'company_name', 'registration_number', 'email',
            'phone_number', 'address', 'status', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_registration_number(self, value):
        val = value.strip().upper()
        qs = Employer.all_objects.filter(registration_number=val)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An employer with this registration number already exists.")
        return val
