from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser, models.Model):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    email = models.EmailField(unique=True)
