from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from allauth.account.adapter import DefaultAccountAdapter
from .managers import UserManager
from .models import User


class AccountAdapter(DefaultAccountAdapter):
    """
    Used only for integration with framework and external tools.
    """

    user_manager: UserManager = User.objects
    
    account_error_messages = {
        'email_blacklisted': _('Email is blacklisted'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages.update(self.account_error_messages)

    def should_send_confirmation_mail(self, *args, **kwargs) -> bool:
        return getattr(settings, 'ACCOUNT_SEND_SIGNUP_CONFIRMATION_MAIL', True)

    def clean_email(self, email):
        try:
            return self.clean_username(email)
        except ValidationError as e:
            if e.code == 'username_taken':
                raise self.validation_error('email_taken')
            elif e.code == 'username_blacklisted':
                raise self.validation_error('email_blacklisted')
            raise e

    def save_user(self, request, user, form, **kwargs):
        data = form.cleaned_data
        email = data.get("email")
        password = data.get("password", data.get("password1"))
        return self.user_manager.create_user(email, password)
