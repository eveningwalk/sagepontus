from django.db import models

class ResponseSet(models.Model):
    session_key = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

class Response(models.Model):
    response_set = models.ForeignKey(
        ResponseSet,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    question_id = models.CharField(max_length=100)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
