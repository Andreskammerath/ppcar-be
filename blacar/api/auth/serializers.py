from rest_framework import serializers
from dj_rest_auth.serializers import LoginSerializer as RestLoginSerializer
from dj_rest_auth.registration.serializers import RegisterSerializer as RestRegisterSerializer


class LoginSerializer(RestLoginSerializer):
    username = None  # Remove username field
    email = serializers.EmailField(required=True)
    
    def authenticate(self, **kwargs):
        return super().authenticate(
            email=kwargs.get('email'),
            password=kwargs.get('password')
        )


class RegisterSerializer(RestRegisterSerializer):
    username = None # Remove username field
    _has_phone_field = False
    
    def validate(self, attrs):
        attrs['username'] = attrs['email']
        return super().validate(attrs)
