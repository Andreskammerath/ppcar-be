
from functools import wraps
from django.db import transaction
from returns.result import Result
from returns.pipeline import is_successful


def atomic(func):
    """ Makes django transactions.atomic decorator Results friendly. """
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            result = func(*args, **kwargs)
            if isinstance(result, Result) and not is_successful(result):
                raise result.failure()
            return result
    
    return wrapper
