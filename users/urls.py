from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CitiesAPIView,
    CountriesAPIView,
    CurrentTimezoneAPIView,
    LocationAutocompleteAPIView,
    NotificationSettingsAPIView,
    ProfileSettingsAPIView,
    ResendActivationEmailView,
    TimezonesAPIView,
    UserPreferencesViewSet, 
    PrayerMethodViewSet, 
    PrayerOffsetViewSet, 
    UserRegistrationView, 
    UserViewSet,
    AccountActivationView,
    PasswordResetView,
    PasswordResetConfirmView,
    create_admin_view,
    CustomTokenObtainPairView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'user-preferences', UserPreferencesViewSet, basename='user-preferences')
router.register(r'prayer-methods', PrayerMethodViewSet, basename='prayer-method')
router.register(r'prayer-offsets', PrayerOffsetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='user_registration'),
    path('activate/<str:token>/', AccountActivationView.as_view(), name='activate-account'),
    path('resend-activation/<str:email>/', ResendActivationEmailView, name='resend-activation'),
    path('reset-password/', PasswordResetView.as_view(), name='reset-password'),
    path('reset-password/<str:token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    path('create-admin/', create_admin_view, name='create_admin'),
    path('login/', CustomTokenObtainPairView.as_view(), name='custom_token_obtain_pair'),
    path('notifications/settings/', NotificationSettingsAPIView.as_view(), name='notification-settings'),
    path('profile/settings/', ProfileSettingsAPIView.as_view(), name='profile-settings'),
    path('timezones/', TimezonesAPIView.as_view(), name='timezones'),
    path('timezone/current/', CurrentTimezoneAPIView.as_view(), name='current-timezone'),

    # Location endpoints
    path('countries/', CountriesAPIView.as_view(), name='countries'),
    path('cities/', CitiesAPIView.as_view(), name='cities'),
    path('locations/autocomplete/', LocationAutocompleteAPIView.as_view(), name='location-autocomplete'),
]
# git add . && 