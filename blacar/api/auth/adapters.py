from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    
    def should_send_confirmation_mail(self, request, email_address, signup) -> bool:
        return getattr(settings, 'ACCOUNT_SEND_SIGNUP_CONFIRMATION_MAIL', True)
