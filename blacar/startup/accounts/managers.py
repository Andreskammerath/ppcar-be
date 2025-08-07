from returns.pipeline import is_successful
from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    """
    Used only for integration with framework and external tools.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        result = self.model.create(email, password)
        if not is_successful(result):
            raise result.failure()
        return result
    
    def create_superuser(self, email, password=None, **extra_fields):
        result = self.model.create_superuser(email, password)
        if not is_successful(result):
            raise result.failure()
        return result
