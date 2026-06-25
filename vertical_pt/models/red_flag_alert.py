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

    # ── Alarm Action: 임상가 의도 기록 ──────────────────────────────────
    monitoring_flagged    = models.BooleanField(default=False)
    monitoring_flagged_at = models.DateTimeField(null=True, blank=True)

    # ── Phase 1: 리퍼럴 추적 ─────────────────────────────────────────
    referral_sent_at          = models.DateTimeField(null=True, blank=True)
    referral_sent_to_email    = models.EmailField(blank=True)
    referral_email_delivered  = models.BooleanField(default=False)  # SMTP 발송 성공 여부
    referral_followup_checked = models.BooleanField(default=False)  # PT 수동 확인 여부
    referral_followup_at      = models.DateTimeField(null=True, blank=True)
    referral_faxed_at         = models.DateTimeField(null=True, blank=True)
    referral_faxed_to         = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.alarm_level} | {self.condition} | {self.timeline.patient_id}"
