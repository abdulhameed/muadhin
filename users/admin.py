from django.contrib import admin
from .models import CustomUser, UserPreferences, Location, PrayerMethod, PrayerOffset, SubscriptionTier

# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'sex', 'city', 'country', 'timezone', 'phone_number', 'last_scheduled_time', 'midnight_utc')


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_methods', 'daily_prayer_summary_enabled', 'daily_prayer_summary_message_method', 'pre_prayer_reminder_enabled', 'pre_prayer_reminder_method', 'pre_prayer_reminder_time', 'adhan_call_enabled', 'adhan_call_method')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'timezone')


@admin.register(PrayerMethod)
class PrayerMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_name')


@admin.register(PrayerOffset)
class PrayerOffsetAdmin(admin.ModelAdmin):
    list_display = ('user', 'imsak', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'sunset', 'isha', 'midnight', 'created_at', 'updated_at')


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
