from celery import Celery, shared_task
from celery.schedules import crontab
# from .models import User  # Import your user profile model
from SalatTracker.models import DailyPrayer, PrayerTime
from SalatTracker.tasks import fetch_and_save_daily_prayer_times, schedule_notifications_for_day, schedule_phone_calls_for_day, send_daily_prayer_message
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, timedelta
from django.core.cache import cache
from rest_framework.response import Response
import requests
from django.utils import timezone

from users.models import PrayerMethod


User = get_user_model()

app = Celery('users')


@shared_task
def check_and_schedule_daily_tasks():
    user_profiles = User.objects.all()
    now = timezone.now()  # Get the current time in UTC

    for user_profile in user_profiles:
        user_midnight_utc = datetime.combine(now.date(), user_profile.midnight_utc, tzinfo=pytz.utc)
        next_hour_utc = now + timedelta(hours=1)
        if (
            user_midnight_utc <= next_hour_utc
            or (not user_profile.last_scheduled_time or now - user_profile.last_scheduled_time > timedelta(hours=24))
        ):
            next_date = now.date() + timedelta(days=1)
            fetch_and_save_daily_prayer_times.delay(user_profile.id, next_date)
            user_profile.last_scheduled_time = now
            user_profile.save()


# @shared_task
# def check_and_schedule_daily_tasks():
#     user_profiles = User.objects.all()
#     processed_users_key = f"processed_users_{datetime.now().date()}"  # Key for the current date
#     # processed_users = cache.get(processed_users_key, set())  # Get processed users from cache
#     user_count = user_profiles.count()
#     print(f"Number of users: {user_count}")
#     for user_profile in user_profiles:
#         user_timezone = pytz.timezone(user_profile.timezone)
#         now = user_timezone.localize(datetime.now())
#         midnight = user_profile.next_midnight

#         last_scheduled = user_profile.last_scheduled_time
#         # Check if the user's midnight falls within the next hour
#         if (
#             midnight <= now + timedelta(hours=1)
#             # and user_profile.id not in processed_users
#             and (not last_scheduled or now - last_scheduled > timedelta(hours=24))
#         ):
#             # Run the fetch_and_save_daily_prayer_times task for the user
#             fetch_and_save_daily_prayer_times.delay(user_profile.id)
#             # processed_users.add(user_profile.id)  # Add the user to the processed set
#             user_profile.last_scheduled_time = now
#             user_profile.save()

    # cache.set(processed_users_key, processed_users)  # Store processed users in cache


@shared_task
def fetch_and_save_daily_prayer_times(user_id, date):
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
        send_daily_prayer_message.delay(user.id)
        schedule_notifications_for_day.delay(user_id, gregorian_date_formatted)
        schedule_phone_calls_for_day.delay(user_id, gregorian_date_formatted)

        return Response(response_data)

        # Call the function to send the notification
        # send_daily_prayer_notification(user)
    else:
        # Handle the error case
        return Response("Failed to fetch prayer times", status=400)
