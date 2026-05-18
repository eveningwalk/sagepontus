from django.db import models
from .patient_timeline import PatientTimeline


class RedFlagAlert(models.Model):
    """Red / Yellow 알람 이력 — 센터장 대시보드 및 리퍼럴 레터 원천."""

    ALARM_CHOICES = [
        ("RED",    "Red — 즉시 리퍼럴"),
        ("YELLOW", "Yellow — 주의 관찰"),
    ]

    timeline            = models.ForeignKey(PatientTimeline, on_delete=models.CASCADE, related_name="alerts")
    condition           = models.CharField(max_length=50)           # cauda_equina, fracture …
    alarm_level         = models.CharField(max_length=10, choices=ALARM_CHOICES)
    matched_indicators  = models.JSONField(default=list)            # 매칭된 증상 라벨 목록
    score               = models.FloatField(default=0.0)
    trigger_label       = models.CharField(max_length=200, blank=True)  # standalone trigger 이름

    referral_letter     = models.TextField(blank=True)              # 생성된 리퍼럴 레터 텍스트
    acknowledged        = models.BooleanField(default=False)        # 센터장 확인 여부
    acknowledged_at     = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.alarm_level} | {self.condition} | {self.timeline.patient_id}"
