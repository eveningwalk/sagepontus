from django.contrib.auth.models import User
from django.db import models


class PilotFeedback(models.Model):
    CAT_BUG         = "bug"
    CAT_IMPROVEMENT = "improvement"
    CAT_PRAISE      = "praise"
    CAT_QUESTION    = "question"
    CAT_CHOICES = [
        (CAT_BUG,         "버그"),
        (CAT_IMPROVEMENT, "개선 제안"),
        (CAT_PRAISE,      "칭찬"),
        (CAT_QUESTION,    "질문"),
    ]

    user       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    category   = models.CharField(max_length=20, choices=CAT_CHOICES, default=CAT_IMPROVEMENT)
    message    = models.TextField()

    # 자동 수집 컨텍스트
    page_url    = models.CharField(max_length=300, blank=True)
    patient_id  = models.CharField(max_length=100, blank=True)
    doc_type    = models.CharField(max_length=50, blank=True)
    action_log  = models.JSONField(default=list, blank=True)  # 최근 액션 5개

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.category}] {self.message[:40]}"
