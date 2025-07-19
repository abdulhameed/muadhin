from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    NotificationSettingsAPIView,
    ProfileSettingsAPIView,
    ResendActivationEmailView,
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
    path('api/register/', UserRegistrationView.as_view(), name='user_registration'),
    path('api/activate/<str:token>/', AccountActivationView.as_view(), name='activate-account'),
    path('api/resend-activation/<str:email>/', ResendActivationEmailView, name='resend-activation'),
    path('api/reset-password/', PasswordResetView.as_view(), name='reset-password'),
    path('api/reset-password/<str:token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    path('create-admin/', create_admin_view, name='create_admin'),
    path('api/login/', CustomTokenObtainPairView.as_view(), name='custom_token_obtain_pair'),
    path('notifications/settings/', NotificationSettingsAPIView.as_view(), name='notification-settings'),
    path('profile/settings/', ProfileSettingsAPIView.as_view(), name='profile-settings'),
]
# git add . && git commit -m "Add user management API endpoints and router configuration" && git push origin merge-supa-render