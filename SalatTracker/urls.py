from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PrayerTimeViewSet, PrayerTimeFetch, DailyPrayerViewSet, DashboardAPIView
from .trigger_urls import trigger_urlpatterns
# from .sync_urls import sync_urlpatterns

router = DefaultRouter()
router.register(r'prayer-times', PrayerTimeViewSet)
router.register(r'daily-prayers', DailyPrayerViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('prayer-times-fetch/<int:user_id>/', PrayerTimeFetch.as_view()),
    path('prayer-times/<int:user_id>/<str:prayer_date>/', PrayerTimeViewSet.as_view({'get': 'get_prayer_times_for_user_and_day'}), name='get_prayer_times_for_user_and_day'),
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),

    *trigger_urlpatterns,

    # *sync_urlpatterns,
]
