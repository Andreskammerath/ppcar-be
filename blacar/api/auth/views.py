from dj_rest_auth.views import LoginView as RestLoginView
from dj_rest_auth.registration.views import RegisterView as RestRegisterView
from .serializers import LoginSerializer, RegisterSerializer


class LoginView(RestLoginView):
    serializer_class = LoginSerializer


class RegisterView(RestRegisterView):
    serializer_class = RegisterSerializer
