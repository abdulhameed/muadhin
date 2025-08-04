from django.urls import path
from .views import ProviderStatusAPIView, AdminProviderAnalyticsAPIView, TestNotificationAPIView

urlpatterns = [
    path('provider-status/', ProviderStatusAPIView.as_view(), name='provider-status'),
    path('admin/analytics/', AdminProviderAnalyticsAPIView.as_view(), name='admin-analytics'),
    path('test-notification/', TestNotificationAPIView.as_view(), name='test-notification'),
]
