import requests
from datetime import datetime
from SalatTracker.tasks import schedule_notifications_for_day, schedule_phone_calls_for_day, send_daily_prayer_summary_message
from users.models import CustomUser, PrayerMethod
from .models import PrayerTime
from django.utils import timezone
from rest_framework.response import Response
from datetime import datetime
from django.utils import timezone
from .models import DailyPrayer, PrayerTime
from django.contrib.auth import get_user_model


User = get_user_model()


# Not being used
def fetch_and_save_prayer_times(user_id, date):
    user = User.objects.get(pk=user_id)
    prayer_method = PrayerMethod.objects.get(user=user)

    api_url = "http://api.aladhan.com/v1/timingsByCity"
    params = {
        "date": date,
        "city": user.city,
        "country": user.country,
        "method": prayer_method.id,
    }

    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json().get("data", {}).get("timings", {})
        date_info = response.json()["data"]["date"]["gregorian"]
        gregorian_date = date_info['date']
        gregorian_weekday = date_info['weekday']['en']

        # Parse date
        gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")
        gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

        daily_prayer, created = DailyPrayer.objects.get_or_create(
            user=user,
            prayer_date=gregorian_date_formatted,
            defaults={
                "weekday_name": gregorian_weekday,
            }
        )
        if not created:
            daily_prayer.weekday_name = gregorian_weekday
            daily_prayer.save()

        response_data = {
                "timings": data,
                "gregorian_date": gregorian_date,
                "gregorian_weekday": gregorian_weekday,
            }

        for prayer_name, prayer_time in data.items():
            prayer_time_obj, created = PrayerTime.objects.get_or_create(
                daily_prayer=daily_prayer,
                prayer_name=prayer_name,
                defaults={
                    "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
                }
            )
            if not created:
                prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')
                prayer_time_obj.save()
                
        # Call the function to send the daily prayer message
        send_daily_prayer_summary_message.delay(user.id)
        schedule_notifications_for_day.delay(user_id, gregorian_date_formatted)
        schedule_phone_calls_for_day.delay(user_id, gregorian_date_formatted)

        return Response(response_data)
