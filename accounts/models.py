from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    supervisor_email = models.EmailField(blank=True, default="")

    def __str__(self):
        return f"{self.user.username} profile"


class Persona(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    description = models.TextField()


class EarlyAccessSignup(models.Model):
    INDUSTRY_CHOICES = [
        ('physical_therapy', '물리치료 / 재활치료'),
        ('sports_medicine', '스포츠의학'),
        ('orthopedics', '정형외과'),
        ('healthcare_general', '헬스케어 일반'),
        ('other', '기타'),
    ]

    email = models.EmailField(unique=True)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_industry_display()})"