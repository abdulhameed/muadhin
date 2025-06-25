from django.contrib import admin
from .models import DailyPrayer, PrayerTime


class PrayerTimeInline(admin.TabularInline):  # You can use admin.StackedInline for a different display style
    model = PrayerTime
    extra = 0  # To remove the extra empty forms
    

class PrayerTimeAdmin(admin.ModelAdmin):
    list_display = ('prayer_name', 'prayer_time', 'is_sms_notified', 'is_phonecall_notified')
    list_filter = ('daily_prayer__user', 'prayer_name')
    search_fields = ('daily_prayer__user__username', 'prayer_name')
    list_select_related = ('daily_prayer__user',)  # Optimize to select related user
    list_per_page = 20

class DailyPrayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'prayer_date', 'weekday_name')
    list_filter = ('user', 'prayer_date')
    search_fields = ('user__username', 'prayer_date')
    list_select_related = ('user',)  # Optimize to select related user
    inlines = [PrayerTimeInline]  # Display related PrayerTime instances inline

# Register the models and their admin classes
admin.site.register(PrayerTime, PrayerTimeAdmin)
admin.site.register(DailyPrayer, DailyPrayerAdmin)
