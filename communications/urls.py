from django.urls import path
from .views import (
    ProviderStatusAPIView,
    AdminProviderAnalyticsAPIView,
    TestNotificationAPIView,
    africas_talking_voice_callback,
    africas_talking_voice_events
    )

urlpatterns = [
    path('provider-status/', ProviderStatusAPIView.as_view(), name='provider-status'),
    path('admin/analytics/', AdminProviderAnalyticsAPIView.as_view(), name='admin-analytics'),
    path('test-notification/', TestNotificationAPIView.as_view(), name='test-notification'),
    # Africa's Talking voice callbacks
    path('callbacks/africastalking/voice/', africas_talking_voice_callback, name='at-voice-callback'),
    path('callbacks/africastalking/voice/events/', africas_talking_voice_events, name='at-voice-events'),

]
