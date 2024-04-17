from django.contrib import admin
from .models import CustomUser, UserPreferences, Location, PrayerMethod, PrayerOffset

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'sex', 'city', 'country', 'timezone', 'phone_number')
    # Add other admin options as needed

@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'city', 'country', 'notification_methods', 'utc_time_for_1159')
    # Add other admin options as needed

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'timezone')
    # Add other admin options as needed

@admin.register(PrayerMethod)
class PrayerMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_name')
    # Add other admin options as needed

@admin.register(PrayerOffset)
class PrayerOffsetAdmin(admin.ModelAdmin):
    list_display = ('user', 'imsak', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'sunset', 'isha', 'midnight', 'created_at', 'updated_at')
    # Add other admin options as needed


# Register the admin classes for your models
# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(UserPreferences, UserPreferencesAdmin)
# admin.site.register(Location, LocationAdmin)
# admin.site.register(PrayerMethod, PrayerMethodAdmin)
# admin.site.register(PrayerOffset, PrayerOffsetAdmin)
