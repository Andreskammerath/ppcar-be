from django.urls import path
from api.accounts.views import AccountProfileViewSet
from .router import router


urlpatterns = [
    path('profile/', AccountProfileViewSet.as_view({'get': 'retrieve'}), name='profile'),
]
urlpatterns += router.urls
