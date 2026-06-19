from django.contrib.auth.models import User
from django.db import models


class PTProfile(models.Model):
    ROLE_CHOICES = [
        ("PT",    "Physical Therapist"),
        ("PTA",   "PT Assistant"),
        ("ADMIN", "Clinic Admin"),
    ]

    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="pt_profile")
    role          = models.CharField(max_length=10, choices=ROLE_CHOICES, default="PT")
    clinic_name   = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "PT Profile"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
