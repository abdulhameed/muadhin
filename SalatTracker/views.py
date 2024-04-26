from rest_framework import viewsets

from SalatTracker.tasks import fetch_and_save_prayer_times
from .models import PrayerTime
from .serializers import PrayerTimeSerializer, DailyPrayerSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
import requests
from users.models import CustomUser, PrayerMethod
from .models import PrayerTime, DailyPrayer
from rest_framework.decorators import action
from django.utils import timezone


class DailyPrayerViewSet(viewsets.ModelViewSet):
    queryset = DailyPrayer.objects.all()
    serializer_class = DailyPrayerSerializer

    @action(detail=False, methods=['GET'])
    def get_daily_prayer_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            serializer = DailyPrayerSerializer(daily_prayer)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response("Daily prayer not found for the given user and date", status=404)


class PrayerTimeViewSet(viewsets.ModelViewSet):
    queryset = PrayerTime.objects.all()
    serializer_class = PrayerTimeSerializer

    @action(detail=False, methods=['GET'])
    def get_prayer_times_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            prayer_times = daily_prayer.prayertime_set.all()  # Assuming you have a related name for the reverse relationship in DailyPrayer model
            serializer = PrayerTimeSerializer(prayer_times, many=True)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response("Prayer times not found for the given user and date", status=404)


class PrayerTimeFetch(APIView):
    def get(self, request, user_id):
        user = CustomUser.objects.get(pk=user_id)
        prayer_method = PrayerMethod.objects.get(user=user)
        date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))
        fetch_and_save_prayer_times(user_id, date)
        return Response("Prayer times are being fetched and saved.")
