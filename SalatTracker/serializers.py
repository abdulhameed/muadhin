from rest_framework import serializers
from .models import PrayerTime, DailyPrayer

class PrayerTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerTime
        fields = '__all__'


class DailyPrayerSerializer(serializers.ModelSerializer):
    prayer_times = PrayerTimeSerializer(many=True, read_only=True)

    class Meta:
        model = DailyPrayer
        fields = '__all__'