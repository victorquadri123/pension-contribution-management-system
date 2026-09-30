from rest_framework import serializers
from apps.jobs.models import JobExecutionLog, NotificationLog, InterestAccrual

class JobExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExecutionLog
        fields = '__all__'


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = '__all__'


class InterestAccrualSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    rsa_pin = serializers.CharField(source='member.rsa_pin', read_only=True)

    class Meta:
        model = InterestAccrual
        fields = '__all__'
