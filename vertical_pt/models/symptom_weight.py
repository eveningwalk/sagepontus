from django.db import models


class SymptomWeight(models.Model):
    """프로토콜별 증상 가중치 매트릭스 — seed_red_flag.py로 적재."""

    ALARM_CHOICES = [
        ("RED",    "Red"),
        ("YELLOW", "Yellow"),
    ]

    protocol_id          = models.CharField(max_length=50, db_index=True)
    symptom_id           = models.CharField(max_length=50)
    label                = models.CharField(max_length=200)
    weight               = models.FloatField()
    alarm_level          = models.CharField(max_length=10, choices=ALARM_CHOICES, default="YELLOW")
    condition_ref        = models.CharField(max_length=50)
    is_standalone_trigger = models.BooleanField(default=False)
    cluster              = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = [("protocol_id", "symptom_id")]
        ordering = ["protocol_id", "-weight"]

    def __str__(self):
        return f"{self.protocol_id} / {self.symptom_id} ({self.weight})"
