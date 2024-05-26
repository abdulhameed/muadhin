from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserPreferencesViewSet, PrayerMethodGenSerializer, PrayerOffsetViewSet, UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'user-preferences', UserPreferencesViewSet)
router.register(r'gen-prayer-methods', PrayerMethodGenSerializer)
router.register(r'prayer-offsets', PrayerOffsetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
