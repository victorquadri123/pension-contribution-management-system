from datetime import date
from rest_framework import serializers
from apps.members.models import CustomUser, Member
from apps.employers.serializers import EmployerSerializer
from apps.employers.models import Employer

class MemberUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'role']
        read_only_fields = ['id', 'role']


class MemberSerializer(serializers.ModelSerializer):
    user = MemberUserSerializer(read_only=True)
    employer = EmployerSerializer(read_only=True)
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=Employer.objects.filter(is_active=True, status=Employer.Status.ACTIVE),
        source='employer',
        write_only=True,
        required=False,
        allow_null=True
    )
    age = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'user', 'employer', 'employer_id', 'rsa_pin', 'nin',
            'date_of_birth', 'age', 'gender', 'address', 'status',
            'is_onboarded', 'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'rsa_pin', 'age', 'is_onboarded', 'is_deleted', 'created_at', 'updated_at']

    def get_age(self, obj):
        return obj.calculate_age()

    def validate_date_of_birth(self, value):
        if value:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 18:
                raise serializers.ValidationError("Member must be at least 18 years old.")
            if age > 70:
                raise serializers.ValidationError("Member age cannot exceed 70 years.")
        return value

    def validate_nin(self, value):
        if value:
            val = value.strip()
            if not val.isdigit() or len(val) != 11:
                raise serializers.ValidationError("NIN must be exactly 11 numeric digits.")
        return value


class MemberRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        val = value.strip().lower()
        if CustomUser.objects.filter(email=val).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return val


class MemberOnboardingSerializer(serializers.Serializer):
    employer_id = serializers.IntegerField()
    date_of_birth = serializers.DateField()
    nin = serializers.CharField(max_length=11)
    gender = serializers.ChoiceField(choices=Member.Gender.choices, required=False)
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_employer_id(self, value):
        if not Employer.objects.filter(pk=value, is_active=True, status=Employer.Status.ACTIVE).exists():
            raise serializers.ValidationError("Selected employer is invalid or inactive.")
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("Member must be at least 18 years old.")
        if age > 70:
            raise serializers.ValidationError("Member age cannot exceed 70 years.")
        return value

    def validate_nin(self, value):
        val = value.strip()
        if not val.isdigit() or len(val) != 11:
            raise serializers.ValidationError("NIN must be exactly 11 numeric digits.")
        return val
