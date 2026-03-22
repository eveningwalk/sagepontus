from django.db import models
from django.contrib.auth.models import User

# Create your models here.
# accounts/models.py

class Persona(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)  # ex. 창업자, PM
    description = models.TextField()