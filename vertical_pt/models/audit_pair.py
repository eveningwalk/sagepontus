from django.contrib.auth.models import User
from django.db import models

from .patient_timeline import PatientTimeline
from .red_flag_alert import RedFlagAlert


class AuditPair(models.Model):
    """
    임상가의 AI 출력 교정 행위를 (원본, 수정본) 쌍으로 저장.
    Phase 7 데이터 수집 레이어 — 향후 weight 갱신 및 fine-tuning 원천.
    """

    TYPE_SOAP     = "soap"
    TYPE_ALARM    = "alarm"
    TYPE_DOCUMENT = "document"
    TYPE_CHOICES  = [
        (TYPE_SOAP,     "SOAP 수정"),
        (TYPE_ALARM,    "Alarm 결정"),
        (TYPE_DOCUMENT, "문서 수정"),
    ]

    DECISION_ADOPTED  = "ADOPTED"
    DECISION_REJECTED = "REJECTED"
    DECISION_MODIFIED = "MODIFIED"
    DECISION_CHOICES  = [
        (DECISION_ADOPTED,  "채택"),
        (DECISION_REJECTED, "기각"),
        (DECISION_MODIFIED, "수정 후 채택"),
    ]

    type      = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    timeline  = models.ForeignKey(PatientTimeline, on_delete=models.CASCADE, related_name="audit_pairs")
    alert     = models.ForeignKey(RedFlagAlert, null=True, blank=True, on_delete=models.CASCADE, related_name="decisions")
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="audit_pairs")

    # SOAP / Document 쌍
    original_content = models.TextField(blank=True)
    edited_content   = models.TextField(blank=True)

    # Alarm 결정
    decision        = models.CharField(max_length=20, choices=DECISION_CHOICES, blank=True)
    decision_reason = models.TextField(blank=True)

    # Document 구분자
    doc_type = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["therapist", "type"]),
            models.Index(fields=["timeline", "type"]),
        ]

    def __str__(self):
        return f"AuditPair [{self.type}] timeline={self.timeline_id} therapist={self.therapist_id}"
