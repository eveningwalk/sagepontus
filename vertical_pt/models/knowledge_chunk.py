from django.db import models


class KnowledgeChunk(models.Model):
    SOURCE_MCID    = "mcid"
    SOURCE_APTA_CPG = "apta_cpg"
    SOURCE_CHOICES = [
        (SOURCE_MCID,     "MCID Reference"),
        (SOURCE_APTA_CPG, "APTA Clinical Practice Guideline"),
    ]

    source    = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    title     = models.CharField(max_length=200)
    condition = models.CharField(max_length=100, blank=True, db_index=True)
    content   = models.TextField()
    embedding = models.JSONField(default=list, blank=True)  # float list; pgvector upgrade later
    meta      = models.JSONField(default=dict, blank=True)  # section, page, url, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["source", "condition"])]

    def __str__(self):
        return f"[{self.source}] {self.title[:60]}"
