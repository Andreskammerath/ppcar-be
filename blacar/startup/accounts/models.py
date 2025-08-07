from django.db import models
from django.contrib.auth.models import AbstractUser
from returns.result import safe, Result, Success
from startup.shared.models import AbstractRoot
from startup.accounts.managers import UserManager


class User(AbstractRoot, AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password']
    EMAIL_FIELD = 'email'
    username = None
    
    email = models.EmailField(unique=True)
    
    objects = UserManager()
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('username', None) # ignored as we removed it
        super().__init__(*args, **kwargs)
    
    @classmethod
    @safe(exceptions=(ValueError,))
    def create(cls, email, password = None) -> Result[AbstractUser, ValueError]:
        new_user = cls.objects._create_user_object(
            username="(empty)", # ignored as we removed it
            email=email,
            password=password,
            is_staff=False,
            is_superuser=False
        )
        new_user.save() # TODO: Handle this with repository at app/features layer
        return Success(new_user)
    
    @classmethod
    @safe(exceptions=(ValueError,))
    def create_superuser(cls, email, password = None) -> Result[AbstractUser, ValueError]:
        new_user = cls.objects._create_user_object(
            username="(empty)", # ignored as we removed it
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        new_user.save() # TODO: Handle this with repository at app/features layer
        return Success(new_user)
