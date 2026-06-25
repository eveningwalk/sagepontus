from django.contrib.auth.models import User
from django.db import models


class InterviewResponse(models.Model):
    TRIGGER_ALARM   = "alarm_fired"
    TRIGGER_REFERRAL = "referral_generated"

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interview_responses")
    trigger    = models.CharField(max_length=40)
    prompt     = models.TextField()
    response   = models.TextField()
    meta       = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} / {self.trigger} @ {self.created_at:%Y-%m-%d %H:%M}"
