from rest_framework import viewsets

from SalatTracker.tasks import fetch_and_save_daily_prayer_times
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
            # FIXED: Use correct related_name
            prayer_times = daily_prayer.prayer_times.all()
            serializer = PrayerTimeSerializer(prayer_times, many=True)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response({"error": "Prayer times not found for the given user and date"}, status=404)


class PrayerTimeFetch(APIView):
    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(pk=user_id)
            # FIXED: Handle missing PrayerMethod
            prayer_method, created = PrayerMethod.objects.get_or_create(
                user=user,
                defaults={'sn': 1, 'name': 'Muslim World League'}
            )
            date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))
            fetch_and_save_daily_prayer_times.delay(user_id, date)
            return Response({"message": "Prayer times are being fetched and saved."})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
