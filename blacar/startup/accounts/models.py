from django.db import models
from django.contrib.auth.models import AbstractUser
from returns.result import Result, Success, Failure
from startup.shared.exceptions import ValidationError
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
    def create(cls, email: str, password: str = None) -> Result[AbstractUser, ValidationError]:
        try:
            new_user = cls.objects._create_user_object(
                username="(empty)", # ignored as we removed it
                email=email.strip().lower(),
                password=password,
                is_staff=False,
                is_superuser=False
            )
            return Success(new_user)
        except ValueError as e:
            msg = str(e)
            return Failure(ValidationError(msg))
    
    @classmethod
    def create_superuser(cls, email: str, password: str = None) -> Result[AbstractUser, ValidationError]:
        try:
            new_user = cls.objects._create_user_object(
                username="(empty)", # ignored as we removed it
                email=email.strip().lower(),
                password=password,
                is_staff=True,
                is_superuser=True
            )
            return Success(new_user)
        except ValueError as e:
            msg = str(e)
            return Failure(ValidationError(msg))
