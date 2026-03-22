from django.db import models
from .category import Category

class Question(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions')
    question_id = models.CharField(max_length=100, unique=True, default='general')
    order = models.PositiveIntegerField(default=0)
    text = models.TextField()
    guidance = models.TextField(blank=True, help_text="입력 가이드를 위한 예시")
    hint = models.TextField(blank=True, help_text="입력 가이드를 위한 설명")

    def __str__(self):
        return f"[{self.category}] {self.text[:30]}"
