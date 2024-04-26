from django.contrib import admin
from .models import CustomUser, UserPreferences, Location, PrayerMethod, PrayerOffset

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'sex', 'city', 'country', 'timezone', 'phone_number')

@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_methods', 'utc_time_for_1159')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'timezone')

@admin.register(PrayerMethod)
class PrayerMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_name')

@admin.register(PrayerOffset)
class PrayerOffsetAdmin(admin.ModelAdmin):
    list_display = ('user', 'imsak', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'sunset', 'isha', 'midnight', 'created_at', 'updated_at')
