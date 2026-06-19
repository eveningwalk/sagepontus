from django.db import models
from django.contrib.auth.models import User
from .patient_timeline import PatientTimeline


class GeneratedDocument(models.Model):
    VERSION_TEMPLATE = "template"
    VERSION_AI = "ai"
    VERSION_CHOICES = [
        (VERSION_TEMPLATE, "Template"),
        (VERSION_AI, "AI"),
    ]

    timeline  = models.ForeignKey(PatientTimeline, on_delete=models.CASCADE, related_name="generated_docs")
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="generated_docs")
    doc_type  = models.CharField(max_length=50)
    version   = models.CharField(max_length=20, choices=VERSION_CHOICES)
    content   = models.TextField()
    chosen    = models.BooleanField(default=False)
    chosen_at = models.DateTimeField(null=True, blank=True)
    generation_params = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["therapist", "doc_type", "chosen"], name="gendoc_thera_dtype_chosen"),
        ]

    def __str__(self):
        return f"{self.doc_type}/{self.version}/chosen={self.chosen}"
