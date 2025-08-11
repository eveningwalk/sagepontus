from django.db import models

# Create your models here.
from django.db import models

 
class ResponseSet(models.Model):
    session_key = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

class Response(models.Model):
    #response_set = models.ForeignKey(ResponseSet, on_delete=models.CASCADE)
    response_set = models.ForeignKey(
        ResponseSet,
        on_delete=models.CASCADE,
        related_name='responses'  # ← 이 줄 추가!
    )
    question_id = models.CharField(max_length=100)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

from django.utils.text import slugify
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True) 
    description = models.TextField(blank=True, help_text="이 카테고리에 대한 간단한 설명")

    def __str__(self):
        return self.name

class Question(models.Model):
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions')
    #category = models.CharField(max_length=100, default='general')
    #category = models.CharField(max_length=100, null=True, blank=True)
    
    question_id = models.CharField(max_length=100, unique=True, default='general')  # ex: 'goal_problem'
    order = models.PositiveIntegerField(default=0)
    text = models.TextField()
    guidance = models.TextField(blank=True, help_text="입력 가이드를 위한 예시")
    hint = models.TextField(blank=True, help_text="입력 가이드를 위한 설명")

    def __str__(self):
        #return f"[{self.category.name}] {self.text[:30]}"
        return f"[{self.category}] {self.text[:30]}"

'''
class Question(models.Model):
    question_id = models.CharField(max_length=100, unique=True)  # ex: 'goal_problem'
    text = models.TextField()                                    # 질문 내용
    example = models.TextField(blank=True, null=True)            # 예시 텍스트
    order = models.PositiveIntegerField(default=0)               # 질문 순서

    def __str__(self):
        return f"{self.order}. {self.text[:30]}"
'''









