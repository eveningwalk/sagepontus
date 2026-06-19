from django.contrib.auth.models import User
from django.db import models


class PatientContact(models.Model):
    ROLE_PHYSICIAN  = "physician"
    ROLE_LAWYER     = "lawyer"
    ROLE_INSURANCE  = "insurance"
    ROLE_OTHER      = "other"
    ROLE_CHOICES = [
        (ROLE_PHYSICIAN, "Physician"),
        (ROLE_LAWYER,    "Lawyer / Attorney"),
        (ROLE_INSURANCE, "Insurance Company"),
        (ROLE_OTHER,     "Other"),
    ]

    therapist    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="patient_contacts")
    patient_id   = models.CharField(max_length=100, db_index=True)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES)
    name         = models.CharField(max_length=120)
    email        = models.EmailField()
    organization = models.CharField(max_length=120, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["role", "name"]
        indexes  = [models.Index(fields=["therapist", "patient_id"])]

    def __str__(self):
        return f"{self.get_role_display()} — {self.name} <{self.email}>"
