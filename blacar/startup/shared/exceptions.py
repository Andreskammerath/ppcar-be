from typing import Optional
from dataclasses import dataclass
from django.core.exceptions import ValidationError as DjangoValidationError


@dataclass
class Error(Exception):
    code: str
    message: Optional[str] = None
    details: Optional[dict] = None


@dataclass(repr=False)
class ValidationError(DjangoValidationError, Error):
    
    def __init__(self, message=None, code: str = "validation_error", details=None, params=None):
        if isinstance(message, list):
            message = [msg for msg in message if msg]
        DjangoValidationError.__init__(self, message or code, code=code, params=params)
        Error.__init__(self, code, self.message, details)
    
    def __str__(self):
        return DjangoValidationError.__str__(self)
