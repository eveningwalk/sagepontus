from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank = True)

    def __str__(self):
        return self.name

class Question(models.Model):
    PURPOSE_CHOICES = [
        ("context", "맥락 탐색"),
        ("motivation", "심리 기반 동기/목표"),
        ("constraint", "조건/제약"),
        ("other", "기타"),
    ]
    
    question_text = models.CharField(max_length=255, default="질문 아직없음")
    block = models.ForeignKey("BrainBlockNode", on_delete=models.CASCADE, related_name="questions_set", null=True, blank=True)
    
    order = models.PositiveIntegerField(default=0)
    question_description = models.TextField(blank=True, default="설명이 아직 없습니다.")
    question_hint = models.CharField(max_length=255, blank=True, default="힌트 없음")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=[
        ("basic", "Basic"),
        ("pro", "Pro"),
    ], default="basic")
    purpose = models.CharField(  # 🔹 질문의 목적 필드 추가
        max_length=20,
        choices=PURPOSE_CHOICES,
        default="context"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "order", "id"]
        unique_together = ("category", "order")

    def __str__(self):
        return self.question_text[:50]


class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("Question", on_delete=models.CASCADE, related_name="answers")
    #node = models.ForeignKey("BrainBlockNode", on_delete=models.CASCADE, related_name="answers", null=True, blank=True)
    brainnode = models.ForeignKey("BrainNode", on_delete=models.CASCADE, related_name="answers", null=True, blank=True)

    
    answer_text = models.TextField()
    inherited_context = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to {self.question.question_text[:30]} (Node {self.brainnode_id})"