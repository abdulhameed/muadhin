from django.urls import path
from .views import (
    ProviderStatusAPIView, 
    AdminProviderAnalyticsAPIView, 
    TestNotificationAPIView, 
    africas_talking_voice_callback
    )

urlpatterns = [
    path('provider-status/', ProviderStatusAPIView.as_view(), name='provider-status'),
    path('admin/analytics/', AdminProviderAnalyticsAPIView.as_view(), name='admin-analytics'),
    path('test-notification/', TestNotificationAPIView.as_view(), name='test-notification'),
    # Africa's Talking voice callback
    path('callbacks/africastalking/voice/', africas_talking_voice_callback, name='at-voice-callback'),

]
