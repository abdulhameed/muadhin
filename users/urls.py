from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ResendActivationEmailView,
    UserPreferencesViewSet, 
    PrayerMethodViewSet, 
    PrayerOffsetViewSet, 
    UserRegistrationView, 
    UserViewSet,
    AccountActivationView,
    PasswordResetView,
    PasswordResetConfirmView,
)
from .views import (
    CustomUserUpdateView, 
    LocationCreateView, 
    LocationUpdateView, 
    PrayerMethodCreateView, 
    PrayerMethodUpdateView, 
    SignUpView, 
    CustomLoginView, 
    UserPreferencesCreateView, 
    UserPreferencesUpdateView, 
    activate_account,
    reset_setup,
    setup_completed,
    step1_user_preferences,
    step2_location,
    step3_prayer_method,
    user_preferences
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'user-preferences', UserPreferencesViewSet)
router.register(r'prayer-methods', PrayerMethodViewSet, basename='prayer-method')
router.register(r'prayer-offsets', PrayerOffsetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api/register/', UserRegistrationView.as_view(), name='user_registration'),
    path('api/activate/<str:token>/', AccountActivationView.as_view(), name='activate-account'),
    path('api/resend-activation/<str:email>/', ResendActivationEmailView, name='resend-activation'),
    path('api/reset-password/', PasswordResetView.as_view(), name='reset-password'),
    path('api/reset-password/<str:token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
# 
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    # path('activate/<uidb64>/<token>/', activate, name='activate'),
    path('api/activate/<str:uidb64>/<str:token>/', activate_account, name='activate-account'),
    #########################
    path('profile/edit/', CustomUserUpdateView.as_view(), name='edit_profile'),
    path('preferences/create/', UserPreferencesCreateView.as_view(), name='create_preferences'),
    path('preferences/edit/', UserPreferencesUpdateView.as_view(), name='edit_preferences'),
    path('location/create/', LocationCreateView.as_view(), name='create_location'),
    path('location/edit/', LocationUpdateView.as_view(), name='edit_location'),
    path('prayer-method/create/', PrayerMethodCreateView.as_view(), name='create_prayer_method'),
    path('prayer-method/edit/', PrayerMethodUpdateView.as_view(), name='edit_prayer_method'),
    path('preferences/', user_preferences, name='user_preferences'),
    path('setup/step1/', step1_user_preferences, name='step1_user_preferences'),
    path('setup/step2/', step2_location, name='step2_location'),
    path('setup/step3/', step3_prayer_method, name='step3_prayer_method'),
    path('setup/completed/', setup_completed, name='setup_completed'),
    path('setup/reset/', reset_setup, name='reset_setup'),
]
