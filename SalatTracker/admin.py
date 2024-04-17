from django.contrib import admin
# from .models import PrayerTime
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

# class PrayerTimeAdmin(admin.ModelAdmin):
#     list_display = ('user', 'prayer_name', 'prayer_time', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified', 'created_at', 'updated_at')
#     list_filter = ('user', 'prayer_name', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified')
#     search_fields = ('user__username', 'prayer_name')
#     date_hierarchy = 'prayer_date'

#     def custom_prayer_list_view(self, request):
#         # Specify the prayer names you want to filter
#         prayer_names = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Sunse', 'Maghrib', 'Isha', 'Imsak', 'Midnight', 'Firstthird', 'Lastthird']

#         # Query the PrayerTime model for the selected prayer names
#         prayer_times = PrayerTime.objects.filter(prayer_name__in=prayer_names)

#         # Create a list of dictionaries to display the data
#         data = []
#         for prayer_time in prayer_times:
#             data.append({
#                 'user': prayer_time.user,
#                 'date': prayer_time.prayer_date,
#                 'prayer_name': prayer_time.prayer_name,
#                 'prayer_time': prayer_time.prayer_time,
#             })

#         # Customize the page title and header
#         self.admin_site.site_header = 'Custom Prayer Time List'
#         self.admin_site.index_title = 'Prayer Times for Selected Names'

#         # Render the custom view
#         return self.render_change_form(request, context={'data': data})

#     custom_prayer_list_view.short_description = "Custom Prayer Time List View"



# admin.site.register(PrayerTime, PrayerTimeAdmin)



# class PrayerTimeAdmin(admin.ModelAdmin):
#     # list_display = ('user', 'prayer_name', 'prayer_time', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified', 'created_at', 'updated_at')
#     list_filter = ('user', 'prayer_name', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified')
#     search_fields = ('user__username', 'prayer_name')
#     date_hierarchy = 'prayer_date'

    # def custom_prayer_list_view(self, request):
    #     # Specify the prayer names you want to filter
    #     prayer_names = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Sunse', 'Maghrib', 'Isha', 'Imsak', 'Midnight', 'Firstthird', 'Lastthird']

    #     # Query the PrayerTime model for the selected prayer names
    #     prayer_times = PrayerTime.objects.filter(prayer_name__in=prayer_names)

    #     # Create a list of dictionaries to display the data
    #     data = []
    #     for prayer_time in prayer_times:
    #         data.append({
    #             'user': prayer_time.user,
    #             'date': prayer_time.prayer_date,
    #             'prayer_name': prayer_time.prayer_name,
    #             'prayer_time': prayer_time.prayer_time,
    #         })

    #     # Customize the page title and header
    #     self.admin_site.site_header = 'Custom Prayer Time List'
    #     self.admin_site.index_title = 'Prayer Times for Selected Names'

    #     # Render the custom view
    #     return self.render_change_form(request, context={'data': data})

    # custom_prayer_list_view.short_description = "Custom Prayer Time List View"


# class CustomPrayerListView(admin.ModelAdmin):
#     list_display = ('user', 'prayer_date', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha')

#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.filter(
#             prayer_name__in=['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
#         ).order_by('user', 'prayer_date')

#     def fajr(self, obj):
#         return obj.get_prayer_time('Fajr')

#     def sunrise(self, obj):
#        return obj.get_prayer_time('Sunrise')

#     def dhuhr(self, obj):
#        return obj.get_prayer_time('Dhuhr')
    
#     def asr(self, obj):
#        return obj.get_prayer_time('Asr')
    
#     def maghrib(self, obj):
#        return obj.get_prayer_time('Maghrib')
    
#     def isha(self, obj):
#        return obj.get_prayer_time('Isha')

#     # and so on for other prayer names...

#     fajr.short_description = 'Fajr'
#     sunrise.short_description = 'Sunrise'
#     dhuhr.short_description = 'Dhuhr'
#     asr.short_description = 'Asr'
#     maghrib.short_description = 'Maghrib'
#     isha.short_description = 'Isha'
    
    # customize column headers

# admin.site.register(PrayerTime, PrayerTimeAdmin) #CustomPrayerListView
# admin.site.register(PrayerTime, CustomPrayerListView)





# class PrayerTimeAdmin(admin.ModelAdmin):
#     list_display = ('user', 'prayer_name', 'prayer_time', 'weekday_name', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified', 'created_at', 'updated_at')
#     list_filter = ('user', 'prayer_name', 'prayer_date', 'is_email_notified', 'is_sms_notified', 'is_phonecall_notified')
#     search_fields = ('user__username', 'prayer_name')
#     date_hierarchy = 'prayer_date'

#     def get_queryset(self, request):
#         # Specify the prayer names you want to filter by
#         prayer_names = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Sunset', 'Maghrib', 'Isha', 'Imsak', 'Midnight', 'Firstthird', 'Lastthird']
        
#         # Get the queryset for the specified prayer names
#         queryset = super().get_queryset(request).filter(prayer_name__in=prayer_names)

#         return queryset

# admin.site.register(PrayerTime, PrayerTimeAdmin)
