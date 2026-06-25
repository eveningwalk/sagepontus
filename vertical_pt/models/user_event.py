from django.contrib.auth.models import User
from django.db import models


class UserEvent(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    event      = models.CharField(max_length=60, db_index=True)
    meta       = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} / {self.event} @ {self.created_at:%Y-%m-%d %H:%M}"
