from rest_framework.routers import DefaultRouter
from .views import trips


router = DefaultRouter()

# Trips views
router.register(r'trips', trips.TripViewSet, basename='trips')
