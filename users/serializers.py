from rest_framework import serializers
from .models import UserPreferences, PrayerMethod, PrayerOffset, CustomUser


class CustomUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(read_only=True)
    # is_superuser = serializers.BooleanField(read_only=True)
    class Meta:
        model = CustomUser
        exclude = ('is_superuser', 'is_staff', 'is_active', 
                   'last_login', 'date_joined', 'groups', 'user_permissions')


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = '__all__'


class PrayerMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerMethod
        fields = '__all__'

class PrayerOffsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerOffset
        fields = '__all__'