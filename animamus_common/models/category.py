from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="이 카테고리에 대한 간단한 설명")

    def __str__(self):
        return self.name
