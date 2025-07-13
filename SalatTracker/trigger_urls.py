from django.urls import path
from .trigger_views import (
    FastDashboardView,
    TriggerFetchPrayerTimesView,
    CheckPrayerAvailabilityView,
    PrayerTimesStatusView
)

# Trigger-based prayer time endpoints
trigger_urlpatterns = [
    # Fast dashboard - returns immediately, signals if fetch needed
    path('fast-dashboard/', FastDashboardView.as_view(), name='fast-dashboard'),
    
    # Trigger prayer time fetch - synchronous, no Celery
    path('trigger-fetch-prayer-times/', TriggerFetchPrayerTimesView.as_view(), name='trigger-fetch-prayer-times'),
    
    # Quick availability check
    path('check-prayer-availability/', CheckPrayerAvailabilityView.as_view(), name='check-prayer-availability'),
    
    # Batch status check for multiple dates
    path('prayer-times-status/', PrayerTimesStatusView.as_view(), name='prayer-times-status'),
]

# git add . && git commit -m "Add trigger-based prayer time endpoints" && git push origin main
# This will add the new trigger-based endpoints to the main URL configuration
# and allow for quick access to prayer time data without relying on Celery tasks.