from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrayerTimeViewSet, PrayerTimeView, DailyPrayerViewSet

router = DefaultRouter()
router.register(r'prayer-times', PrayerTimeViewSet)
router.register(r'daily-prayers', DailyPrayerViewSet)


urlpatterns = [
    path('', include(router.urls)),
    # path('prayer-times-view/', PrayerTimeView.as_view()),
    path('prayer-times-view/<int:user_id>/', PrayerTimeView.as_view()),
    path('prayer-times/<int:user_id>/<str:prayer_date>/', PrayerTimeViewSet.as_view({'get': 'get_prayer_times_for_user_and_day'}), name='get_prayer_times_for_user_and_day'),
]
