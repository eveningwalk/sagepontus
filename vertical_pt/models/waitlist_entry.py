from django.db import models


class WaitlistEntry(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=50, default="landing")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Waitlist Entry"
        verbose_name_plural = "Waitlist Entries"

    def __str__(self):
        return self.email
