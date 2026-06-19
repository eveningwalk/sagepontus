from rest_framework import serializers
from vertical_pt.models import PatientTimeline, RedFlagAlert


class AnalyzeRequestSerializer(serializers.Serializer):
    patient_id   = serializers.CharField(max_length=100)
    soap_text    = serializers.CharField()
    session_date = serializers.DateField(required=False)
    use_ai       = serializers.BooleanField(default=False)
    generate_referral = serializers.BooleanField(default=False)

    def validate_patient_id(self, value):
        return value.strip().upper()


class RedFlagAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RedFlagAlert
        fields = ["id", "condition", "alarm_level", "matched_indicators",
                  "score", "trigger_label", "referral_letter", "created_at"]


class AnalyzeResponseSerializer(serializers.Serializer):
    alarm      = serializers.CharField()
    condition  = serializers.CharField(allow_null=True)
    score      = serializers.FloatField()
    matched    = serializers.ListField(child=serializers.CharField())
    trigger    = serializers.CharField(allow_blank=True)
    alert_id   = serializers.IntegerField(allow_null=True)
    referral_letter = serializers.CharField(allow_blank=True)
    patient_context = serializers.DictField()


class PatientTimelineSerializer(serializers.ModelSerializer):
    alerts = RedFlagAlertSerializer(many=True, read_only=True)

    class Meta:
        model  = PatientTimeline
        fields = ["id", "patient_id", "session_date", "alarm_level",
                  "critical_score", "triggered_condition", "alerts", "created_at"]
