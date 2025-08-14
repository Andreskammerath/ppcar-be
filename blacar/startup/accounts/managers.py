from returns.pipeline import is_successful
from django.db import IntegrityError
from startup.shared.exceptions import ValidationError
from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    """
    Used only for integration with framework and external tools.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        try:
            result = self.model.create(email, password)
            if not is_successful(result):
                raise result.failure()
            user = result.unwrap()
            user.save() # TODO: Handle this with repository at app/features layer
        except IntegrityError as e:
            error_message = str(e).casefold()
            if "unique" in error_message and "email" in error_message:
                raise ValidationError('Email already exists', code='email_taken')
            raise e
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        try:
            result = self.model.create_superuser(email, password)
            if not is_successful(result):
                raise result.failure()
            user = result.unwrap()
            user.save() # TODO: Handle this with repository at app/features layer
        except IntegrityError as e:
            error_message = str(e).casefold()
            if "unique" in error_message and "email" in error_message:
                raise ValidationError('Email already exists', code='email_taken')
            raise e
        return user
