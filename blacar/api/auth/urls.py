from django.urls import path, re_path
from allauth.account.views import ConfirmEmailView
from dj_rest_auth.views import LogoutView
from .views import LoginView, RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    re_path(
        r'^account-confirm-email/(?P<key>[-:\w]+)/$', ConfirmEmailView.as_view(),
        name='account_confirm_email',
    )
]
