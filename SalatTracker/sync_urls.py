from django.urls import path
from .sync_views import (
    SyncDashboardView,
    SyncRefreshView,
    SyncSendSummaryView,
    SyncPrayerTimesView,
    SyncHealthView
)

# New sync-based endpoints (no Celery required)
sync_urlpatterns = [
    # Main dashboard with auto-fetch
    path('sync/dashboard/', SyncDashboardView.as_view(), name='sync-dashboard'),
    
    # Manual refresh prayer times
    path('sync/refresh/', SyncRefreshView.as_view(), name='sync-refresh'),
    
    # Send daily summary email
    path('sync/send-summary/', SyncSendSummaryView.as_view(), name='sync-send-summary'),
    
    # Get prayer times for specific date
    path('sync/prayer-times/', SyncPrayerTimesView.as_view(), name='sync-prayer-times'),
    
    # Health check
    path('sync/health/', SyncHealthView.as_view(), name='sync-health'),
]