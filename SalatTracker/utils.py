import requests
from datetime import datetime
from users.models import CustomUser, PrayerMethod
from .models import PrayerTime
from django.utils import timezone


user = CustomUser


from datetime import datetime
from django.utils import timezone
from .models import DailyPrayer, PrayerTime

def fetch_and_save_prayer_times(user, prayer_method, date=None):
    if not date:
        date = datetime.now().strftime('%d-%m-%Y')

    api_url = "http://api.aladhan.com/v1/timingsByCity"
    
    params = {
        "date": date,
        "city": user.city,  # Get the user's city from the CustomUser model
        "country": user.country,  # Get the user's country from the CustomUser model
        "method": prayer_method.id,  # Use the ID from the selected prayer method
    }

    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json().get("data", {}).get("timings", {})
        date_info = data.get("date", {})

        gregorian_date = date_info['gregorian']['date']
        gregorian_weekday = date_info['gregorian']['weekday']['en']

        daily_prayer, created = DailyPrayer.objects.get_or_create(
            user=user,
            prayer_date=gregorian_date,
            defaults={
                "weekday_name": gregorian_weekday,
            }
        )

        if not created:
            daily_prayer.weekday_name = gregorian_weekday
            daily_prayer.save()

        for prayer_name, prayer_time in data.items():
            prayer_time_obj, created = PrayerTime.objects.get_or_create(
                daily_prayer=daily_prayer,
                prayer_name=prayer_name,
                defaults={
                    "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
                }
            )

            if not created:
                prayer_time_obj.prayer_time = timezone.make_aware(datetime.strptime(prayer_time, '%H:%M'))
                prayer_time_obj.save()


# def fetch_and_save_prayer_times(user, prayer_method, date=None):
#     if not date:
#         date = datetime.now().strftime('%d-%m-%Y')
    
#     api_url = f"http://api.aladhan.com/v1/timingsByCity"

#     prayer_method = PrayerMethod.objects.get(user=user)
    
#     params = {
#         "date": date,
#         "city": user.city,  # Get the user's city from the CustomUser model
#         "country": user.Country,  # Get the user's country from the CustomUser model
#         "method": prayer_method.id,  # Use the ID from the selected prayer method
#     }

#     response = requests.get(api_url, params=params)

#     if response.status_code == 200:
#         print("<<<<<<<<<<>>>>>>>>>>>")
#         print(response.json())
#         data = response.json().get("data", {}).get("timings", {})
#         date_info = data.get("date", {})

#         # Extract gregorian date and weekday name
#         gregorian_date = date_info['gregorian']['date']
#         gregorian_weekday = date_info['gregorian']['weekday']['en']
        
#         for prayer_name, prayer_time in data.items():

#              # Create or update PrayerTime objects
#             prayer_time_obj, created = PrayerTime.objects.get_or_create(
#             user=user,
#             prayer_name=prayer_name,
#                 defaults={
#                     "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
#                     "prayer_date": gregorian_date,
#                     "weekday_name": gregorian_weekday,
#                 }
#             )
#             print("<<<<<<<<<>>>>>>>>>>>")
#             print(prayer_time_obj)
#             print("<<<<<<<<<>>>>>>>>>>>")
#             if not created:
#                 prayer_time_obj.prayer_time = timezone.make_aware(datetime.strptime(prayer_time, '%H:%M'))
#                 prayer_time_obj.prayer_date = gregorian_date
#                 prayer_time_obj.weekday_name = gregorian_weekday
#                 prayer_time_obj.save()
