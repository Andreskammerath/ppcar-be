from django.urls import path, include
from .router import api_router

urlpatterns = [
    path('auth/', include('api.auth.urls')),
]

urlpatterns += api_router.urls
