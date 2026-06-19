from django.db import models
from django.contrib.auth.models import User


class PatientTimeline(models.Model):
    """환자별 세션 누적 — CRA 시계열 추론의 원천 데이터."""

    ALARM_CHOICES = [
        ("RED",    "Red — 즉시 리퍼럴"),
        ("YELLOW", "Yellow — 주의 관찰"),
        ("NONE",   "None — 정상"),
    ]

    therapist    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pt_timelines")
    patient_id   = models.CharField(max_length=100, db_index=True)
    patient_name = models.CharField(max_length=100, blank=True)
    session_date = models.DateField()

    soap_text           = models.TextField()
    extracted_symptoms  = models.JSONField(default=dict)   # VPPA 출력
    clinical_context    = models.JSONField(default=dict, blank=True)  # AI 임상 컨텍스트 추출
    critical_score      = models.FloatField(default=0.0)
    alarm_level         = models.CharField(max_length=10, choices=ALARM_CHOICES, default="NONE")
    triggered_condition = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["patient_id", "session_date"]
        indexes = [
            models.Index(fields=["therapist", "patient_id", "session_date"]),
        ]

    def __str__(self):
        return f"{self.patient_id} / {self.session_date} / {self.alarm_level}"
